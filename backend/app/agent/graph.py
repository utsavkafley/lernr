from typing import TypedDict
from langgraph.graph import StateGraph, END, START
from sqlalchemy.orm import Session
from sqlalchemy import select, func
import anthropic

from app.models import Concept, Question, QuestionConcept, Attempt, UserTrackProgress
from app.config import settings


class TutorState(TypedDict):
    messages: list          # [{"role": "user"|"assistant", "content": str}, ...]
    target_concept: str     # concept currently being drilled
    target_question: dict   # {"id", "prompt", "answer"}
    hint_level: int         # 0–3, how many hints have been given on this question
    user_id: str
    last_evaluation: str    # "correct" | "acceptable" | "incorrect" | ""
    correct_streak: int     # consecutive correct/acceptable on current concept


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_weak_concepts(user_id: str, db: Session) -> list[dict]:
    rows = db.execute(
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
        .having(func.count(Attempt.id) > 0)
    ).all()

    stats = [
        {"id": r.id, "name": r.name, "accuracy": round((r.correct or 0) / r.total, 2)}
        for r in rows
    ]
    return sorted(stats, key=lambda x: x["accuracy"])


def get_concept_questions(concept_name: str, user_id: str, db: Session) -> list[dict]:
    completed_track_ids = db.execute(
        select(UserTrackProgress.track_id).where(
            UserTrackProgress.user_id == user_id,
            UserTrackProgress.completed == True,
        )
    ).scalars().all()

    questions = db.execute(
        select(Question)
        .join(QuestionConcept, QuestionConcept.question_id == Question.id)
        .join(Concept, Concept.id == QuestionConcept.concept_id)
        .where(
            Concept.name == concept_name,
            Question.track_id.in_(completed_track_ids),
        )
        .limit(10)
    ).scalars().all()

    return [{"id": q.id, "prompt": q.prompt, "answer": q.answer} for q in questions]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a Socratic Spanish tutor using the Language Transfer method.
You will be given a specific question to guide the student toward. Stay focused on that exact question.

Rules:
- Never use markdown formatting — plain text only.
- Never reveal the answer directly until hint level 3.
- Keep responses short: 1-3 sentences max.
- Always end with a question that nudges the student toward the answer.
- Be warm and encouraging, never condescending.

Hint level behaviour (follow strictly):
  0 - Rephrase the question in a simpler, more approachable way.
  1 - Break the answer into parts and ask about the first part.
  2 - Give a strong structural hint (e.g. the ending changes to -o for "I"...).
  3 - Give the answer clearly with a one-sentence explanation of why."""


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def build_graph(checkpointer, db: Session):

    # --- entry router ---------------------------------------------------
    def entry_router(state: TutorState) -> str:
        msgs = state.get("messages", [])
        if msgs and msgs[-1]["role"] == "user":
            return "evaluate_response"
        return "select_concept"

    # --- select_concept -------------------------------------------------
    def select_concept(state: TutorState) -> TutorState:
        # Keep current concept unless it was cleared by reinforce
        if state.get("target_concept"):
            return state

        weak = get_weak_concepts(state["user_id"], db)
        concept = weak[0]["name"] if weak else "present tense verbs"
        questions = get_concept_questions(concept, state["user_id"], db)
        question = questions[0] if questions else {}

        return {
            **state,
            "target_concept": concept,
            "target_question": question,
            "hint_level": 0,
            "last_evaluation": "",
            "correct_streak": 0,
        }

    # --- ask_question ---------------------------------------------------
    def ask_question(state: TutorState) -> TutorState:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        q = state.get("target_question", {})
        hint_level = state.get("hint_level", 0)
        concept = state.get("target_concept", "")

        if not state.get("messages"):
            user_prompt = (
                f"The student is working on: '{concept}'.\n"
                f"Start the session by asking them this question using the Socratic method: "
                f"'{q.get('prompt', '')}'. Do not reveal the answer."
            )
        else:
            user_prompt = (
                f"The student is on hint level {hint_level}/3 for concept '{concept}'.\n"
                f"Question: '{q.get('prompt', '')}'\n"
                f"Guide them with a level-{hint_level} hint. Do not reveal the full answer yet."
            )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        ai_text = response.content[0].text.strip()

        return {
            **state,
            "messages": state.get("messages", []) + [{"role": "assistant", "content": ai_text}],
        }

    # --- evaluate_response ----------------------------------------------
    def evaluate_response(state: TutorState) -> TutorState:
        msgs = state.get("messages", [])
        last_human = next(
            (m["content"] for m in reversed(msgs) if m["role"] == "user"), ""
        )
        q = state.get("target_question", {})

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8,
            system=(
                "Evaluate whether the student's Spanish answer is correct. "
                "Reply with exactly one word: correct, acceptable, or incorrect."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Question: {q.get('prompt', '')}\n"
                    f"Expected: {q.get('answer', '')}\n"
                    f"Student said: {last_human}"
                ),
            }],
        )
        verdict = response.content[0].text.strip().lower()
        if verdict not in ("correct", "acceptable", "incorrect"):
            verdict = "incorrect"

        streak = state.get("correct_streak", 0)
        if verdict in ("correct", "acceptable"):
            streak += 1
        else:
            streak = 0

        return {**state, "last_evaluation": verdict, "correct_streak": streak}

    # --- post-eval router -----------------------------------------------
    def post_eval_router(state: TutorState) -> str:
        if state.get("last_evaluation") in ("correct", "acceptable"):
            return "reinforce"
        return "give_hint"

    # --- give_hint ------------------------------------------------------
    def give_hint(state: TutorState) -> TutorState:
        new_level = min(state.get("hint_level", 0) + 1, 3)
        return {**state, "hint_level": new_level}

    # --- reinforce ------------------------------------------------------
    def reinforce(state: TutorState) -> TutorState:
        # Move to a new concept after 3 correct answers on the current one
        if state.get("correct_streak", 0) >= 3:
            return {
                **state,
                "target_concept": "",
                "target_question": {},
                "hint_level": 0,
                "last_evaluation": "",
                "correct_streak": 0,
            }
        # Same concept, new question
        concept = state.get("target_concept", "")
        questions = get_concept_questions(concept, state["user_id"], db)
        current_q_id = state.get("target_question", {}).get("id")
        next_q = next((q for q in questions if q["id"] != current_q_id), None)
        if next_q:
            return {**state, "target_question": next_q, "hint_level": 0, "last_evaluation": ""}
        # No more questions on this concept → move on
        return {
            **state,
            "target_concept": "",
            "target_question": {},
            "hint_level": 0,
            "last_evaluation": "",
            "correct_streak": 0,
        }

    # ---------------------------------------------------------------------------
    # Assemble graph
    # ---------------------------------------------------------------------------

    graph = StateGraph(TutorState)

    graph.add_node("select_concept", select_concept)
    graph.add_node("ask_question", ask_question)
    graph.add_node("evaluate_response", evaluate_response)
    graph.add_node("give_hint", give_hint)
    graph.add_node("reinforce", reinforce)

    # Entry: route based on whether the last message is from the user
    graph.add_conditional_edges(START, entry_router, {
        "select_concept": "select_concept",
        "evaluate_response": "evaluate_response",
    })

    graph.add_edge("select_concept", "ask_question")
    graph.add_edge("ask_question", END)

    graph.add_conditional_edges("evaluate_response", post_eval_router, {
        "reinforce": "reinforce",
        "give_hint": "give_hint",
    })
    graph.add_edge("give_hint", "ask_question")
    graph.add_edge("reinforce", "select_concept")

    return graph.compile(checkpointer=checkpointer)
