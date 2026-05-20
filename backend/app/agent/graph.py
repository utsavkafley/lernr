from typing import TypedDict
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
from sqlalchemy import select, func
import anthropic

from app.models import Concept, Question, QuestionConcept, Attempt, UserTrackProgress
from app.config import settings


class TutorState(TypedDict):
    messages: list
    target_concept: str
    target_question: dict
    hint_level: int
    user_id: str


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
        .order_by(
            (func.count(Attempt.id).filter(
                Attempt.evaluation_state.in_(["correct", "acceptable"])
            ) / func.count(Attempt.id)).asc()
        )
    ).all()
    return [
        {"id": r.id, "name": r.name, "accuracy": round((r.correct or 0) / r.total, 2)}
        for r in rows
    ]


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


SYSTEM_PROMPT = """You are a Socratic Spanish tutor based on the Language Transfer method.
Your role is to guide students to discover answers themselves through questions — never give the answer directly.

When a student struggles:
- hint_level 0: Ask a related simpler question to activate prior knowledge
- hint_level 1: Break the question into smaller steps
- hint_level 2: Give a strong hint (portion of the phrase, pattern reminder)
- hint_level 3: Reveal the answer with a clear explanation

Always be encouraging. Keep responses short (2–4 sentences max).
Never translate directly — always ask "what do you think?" first.
"""


def build_graph(checkpointer, db: Session):
    def select_concept(state: TutorState) -> TutorState:
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
        }

    def ask_question(state: TutorState) -> TutorState:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        q = state.get("target_question", {})
        hint_level = state.get("hint_level", 0)

        if not state["messages"] or hint_level == 0:
            prompt = f"Ask the student this question using the Socratic method: '{q.get('prompt', '')}'. Don't reveal the answer."
        else:
            prompt = f"The student is struggling (hint level {hint_level}/3). Guide them toward '{q.get('prompt', '')}' with a hint appropriate for level {hint_level}."

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        ai_text = response.content[0].text
        return {**state, "messages": state["messages"] + [{"role": "assistant", "content": ai_text}]}

    def evaluate_response(state: TutorState) -> TutorState:
        messages = state["messages"]
        last_human = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        q = state.get("target_question", {})

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8,
            system="Evaluate if the student's answer is correct. Reply with exactly one word: correct, acceptable, or incorrect.",
            messages=[{
                "role": "user",
                "content": f"Question: {q.get('prompt', '')}\nExpected: {q.get('answer', '')}\nStudent said: {last_human}",
            }],
        )
        verdict = response.content[0].text.strip().lower()
        if verdict not in ("correct", "acceptable", "incorrect"):
            verdict = "incorrect"
        return {**state, "messages": messages + [{"role": "system", "content": f"__eval__{verdict}"}]}

    def router_after_eval(state: TutorState) -> str:
        messages = state["messages"]
        last_sys = next(
            (m["content"] for m in reversed(messages) if m["role"] == "system"), ""
        )
        if "__eval__correct" in last_sys or "__eval__acceptable" in last_sys:
            return "reinforce"
        return "give_hint"

    def give_hint(state: TutorState) -> TutorState:
        new_level = min(state.get("hint_level", 0) + 1, 3)
        return {**state, "hint_level": new_level}

    def reinforce(state: TutorState) -> TutorState:
        correct_count = sum(
            1 for m in state["messages"]
            if m["role"] == "system"
            and ("__eval__correct" in m["content"] or "__eval__acceptable" in m["content"])
        )
        if correct_count >= 3:
            return {**state, "target_concept": "", "target_question": {}, "hint_level": 0}
        return state

    graph = StateGraph(TutorState)
    graph.add_node("select_concept", select_concept)
    graph.add_node("ask_question", ask_question)
    graph.add_node("evaluate_response", evaluate_response)
    graph.add_node("give_hint", give_hint)
    graph.add_node("reinforce", reinforce)

    graph.set_entry_point("select_concept")
    graph.add_edge("select_concept", "ask_question")
    graph.add_edge("ask_question", END)
    graph.add_edge("give_hint", "ask_question")
    graph.add_edge("reinforce", "select_concept")
    graph.add_conditional_edges("evaluate_response", router_after_eval, {
        "reinforce": "reinforce",
        "give_hint": "give_hint",
    })

    return graph.compile(checkpointer=checkpointer)
