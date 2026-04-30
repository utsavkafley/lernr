import random
import unicodedata

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Attempt, Question, QuestionConcept, User, UserTrackProgress
from app.schemas import ConceptResponse, QuizQuestionResponse, SubmitAnswerRequest, SubmitAnswerResponse

router = APIRouter(prefix="/quiz", tags=["quiz"])


def _normalize(text: str) -> str:
    return text.strip().lower()


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _llm_evaluate(prompt: str, expected: str, alternates: list, user_answer: str) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    all_accepted = ", ".join([expected] + (alternates or []))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=16,
        system=(
            "You are a Spanish language answer evaluator. "
            "Given a question, the expected answer(s), and a student's answer, "
            "reply with exactly one word: correct, acceptable, or incorrect.\n"
            "correct = matches expected meaning exactly\n"
            "acceptable = correct meaning, minor spelling or word-order variation\n"
            "incorrect = wrong meaning or translation"
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Question: {prompt}\n"
                f"Expected answers: {all_accepted}\n"
                f"Student answer: {user_answer}\n\n"
                "Reply with exactly one word."
            ),
        }],
    )
    verdict = response.content[0].text.strip().lower()
    return verdict if verdict in ("correct", "acceptable", "incorrect") else "incorrect"


def _evaluate(question: Question, user_answer: str) -> str:
    normalized_user = _normalize(user_answer)
    all_expected = [_normalize(question.answer)] + [_normalize(a) for a in (question.alternate_answers or [])]

    if normalized_user in all_expected:
        return "correct"

    stripped_user = _strip_accents(normalized_user)
    if any(stripped_user == _strip_accents(e) for e in all_expected):
        return "acceptable"

    return _llm_evaluate(question.prompt, question.answer, question.alternate_answers, user_answer)


@router.get("/next", response_model=QuizQuestionResponse)
def next_question(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    completed_track_ids = db.execute(
        select(UserTrackProgress.track_id).where(
            UserTrackProgress.user_id == current_user.id,
            UserTrackProgress.completed == True,
        )
    ).scalars().all()

    if not completed_track_ids:
        raise HTTPException(status_code=404, detail="No completed tracks yet")

    all_questions = db.execute(
        select(Question)
        .where(Question.track_id.in_(completed_track_ids))
        .options(
            selectinload(Question.question_concepts).selectinload(QuestionConcept.concept)
        )
    ).scalars().all()

    if not all_questions:
        raise HTTPException(status_code=404, detail="No questions available")

    recent_ids = set(
        db.execute(
            select(Attempt.question_id)
            .where(Attempt.user_id == current_user.id)
            .order_by(Attempt.created_at.desc())
            .limit(settings.recent_attempt_window)
        ).scalars().all()
    )

    pool = [q for q in all_questions if q.id not in recent_ids]
    if len(pool) < settings.min_pool_size:
        pool = list(all_questions)

    concept_rows = db.execute(
        select(
            QuestionConcept.concept_id,
            func.count(Attempt.id).label("total"),
            func.count(Attempt.id).filter(
                Attempt.evaluation_state.in_(["correct", "acceptable"])
            ).label("correct"),
        )
        .join(Attempt, Attempt.question_id == QuestionConcept.question_id)
        .where(Attempt.user_id == current_user.id)
        .group_by(QuestionConcept.concept_id)
    ).all()

    # concept_id → accuracy (0.0–1.0); unseen concepts default to 0.5
    concept_accuracy = {
        r.concept_id: (r.correct / r.total if r.total else 0.5)
        for r in concept_rows
    }

    def _weight(q: Question) -> float:
        ids = [qc.concept_id for qc in q.question_concepts]
        if not ids:
            return 0.5
        return sum(1.0 - concept_accuracy.get(cid, 0.5) for cid in ids) / len(ids)

    weights = [_weight(q) for q in pool]
    if all(w == 0.0 for w in weights):
        weights = [1.0] * len(pool)

    chosen = random.choices(pool, weights=weights, k=1)[0]

    return QuizQuestionResponse(
        question_id=chosen.id,
        prompt=chosen.prompt,
        concepts=[
            ConceptResponse(id=qc.concept.id, name=qc.concept.name)
            for qc in chosen.question_concepts
        ],
    )


@router.post("/submit", response_model=SubmitAnswerResponse)
def submit_answer(
    body: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = db.execute(
        select(Question).where(Question.id == body.question_id)
    ).scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    state = _evaluate(question, body.user_answer)

    db.add(Attempt(
        user_id=current_user.id,
        question_id=question.id,
        user_answer=body.user_answer,
        evaluation_state=state,
    ))
    db.commit()

    if state == "correct":
        feedback = "Correct!"
    elif state == "acceptable":
        feedback = f"Close enough! Expected: {question.answer}"
    else:
        feedback = f"Incorrect. Expected: {question.answer}"

    return SubmitAnswerResponse(
        evaluation_state=state,
        feedback=feedback,
        expected_answer=question.answer,
        alternate_answers=question.alternate_answers or [],
    )
