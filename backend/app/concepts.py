"""Single source of truth for concept progress.

Quiz accuracy is derived from Attempt rows; chat_score is stored in
ConceptProgress (agent-evaluated). The blended score combines them so the
agent, the quiz selector, and the progress view all read the same numbers.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Attempt, Concept, ConceptProgress, QuestionConcept, Track, UserTrackProgress,
)

# How much quiz recall vs. chat-demonstrated understanding count toward mastery.
QUIZ_WEIGHT = 0.7
CHAT_WEIGHT = 0.3
# Chat alone can't fully master a concept — the user must prove it on a quiz.
# A chat-only score is capped just below the mastery threshold so the agent
# always has a reason to nudge the learner toward the quiz.
CHAT_ONLY_CAP = round(settings.mastery_threshold - 0.01, 2)


@dataclass
class ConceptStat:
    concept_id: int
    name: str
    total_attempts: int
    correct_attempts: int
    quiz_accuracy: float   # 0.0–1.0 from quiz attempts
    chat_score: float      # 0.0–1.0 agent-evaluated
    blended: float         # combined score used for mastery / selection
    mastered: bool


# ---------------------------------------------------------------------------
# Track helpers
# ---------------------------------------------------------------------------

def completed_track_ids(user_id, db: Session) -> list[int]:
    return list(
        db.execute(
            select(UserTrackProgress.track_id).where(
                UserTrackProgress.user_id == user_id,
                UserTrackProgress.completed.is_(True),
            )
        ).scalars().all()
    )


def max_completed_track_number(user_id, db: Session) -> int:
    ids = completed_track_ids(user_id, db)
    if not ids:
        return 0
    return db.execute(
        select(func.max(Track.number)).where(Track.id.in_(ids))
    ).scalar() or 0


# ---------------------------------------------------------------------------
# Blended concept stats
# ---------------------------------------------------------------------------

def _blend(quiz_accuracy: float, total_attempts: int, chat_score: float) -> float:
    if total_attempts and chat_score:
        return round(QUIZ_WEIGHT * quiz_accuracy + CHAT_WEIGHT * chat_score, 2)
    if total_attempts:
        return quiz_accuracy
    if chat_score:
        return round(min(chat_score, CHAT_ONLY_CAP), 2)
    return 0.0


def concept_stats(user_id, db: Session) -> list[ConceptStat]:
    """Blended stats for every concept the user has touched (quiz or chat)."""
    quiz_rows = db.execute(
        select(
            Concept.id,
            Concept.name,
            func.count(Attempt.id).label("total"),
            func.count(Attempt.id).filter(
                Attempt.evaluation_state.in_(["correct", "acceptable"])
            ).label("correct"),
        )
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .join(Attempt, Attempt.question_id == QuestionConcept.question_id)
        .where(Attempt.user_id == user_id)
        .group_by(Concept.id, Concept.name)
    ).all()

    chat_by_id = dict(
        db.execute(
            select(ConceptProgress.concept_id, ConceptProgress.chat_score)
            .where(ConceptProgress.user_id == user_id)
        ).all()
    )

    stats: list[ConceptStat] = []
    seen: set[int] = set()

    for r in quiz_rows:
        seen.add(r.id)
        quiz_acc = round((r.correct or 0) / r.total, 2) if r.total else 0.0
        chat = chat_by_id.get(r.id, 0.0)
        blended = _blend(quiz_acc, r.total, chat)
        stats.append(ConceptStat(
            concept_id=r.id,
            name=r.name,
            total_attempts=r.total,
            correct_attempts=r.correct or 0,
            quiz_accuracy=quiz_acc,
            chat_score=chat,
            blended=blended,
            mastered=blended >= settings.mastery_threshold,
        ))

    # Concepts the user has only chatted about (no quiz attempts yet).
    missing = [cid for cid in chat_by_id if cid not in seen]
    if missing:
        for cid, name in db.execute(
            select(Concept.id, Concept.name).where(Concept.id.in_(missing))
        ).all():
            chat = chat_by_id[cid]
            blended = _blend(0.0, 0, chat)
            stats.append(ConceptStat(
                concept_id=cid,
                name=name,
                total_attempts=0,
                correct_attempts=0,
                quiz_accuracy=0.0,
                chat_score=chat,
                blended=blended,
                mastered=blended >= settings.mastery_threshold,
            ))

    return stats


def set_chat_score(user_id, concept_id: int, chat_score: float, db: Session) -> None:
    """Upsert the agent-evaluated chat score for one concept."""
    score = max(0.0, min(1.0, chat_score))
    row = db.execute(
        select(ConceptProgress).where(
            ConceptProgress.user_id == user_id,
            ConceptProgress.concept_id == concept_id,
        )
    ).scalar_one_or_none()

    if row is None:
        row = ConceptProgress(user_id=user_id, concept_id=concept_id)
        db.add(row)

    row.chat_score = score
    row.chat_updated_at = datetime.now(timezone.utc)
    db.commit()
