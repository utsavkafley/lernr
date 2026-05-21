"""
AI Tutor graph — Language Transfer Socratic method.

Architecture:
  Session start  → build_student_model → plan_session → converse → END
  User responds  → evaluate_turn → advance_or_stay  → converse → END
  No eval needed →                                    converse → END

The planner builds a teaching chain: a sequence of steps that bridge from
concepts the student already knows toward the target concept they struggle
with. The conversationalist executes one step at a time, strictly following
the Language Transfer method — it asks, never tells.
"""

import json
from typing import TypedDict

import anthropic
from langgraph.graph import END, START, StateGraph
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attempt, Concept, Question, QuestionConcept, UserTrackProgress


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class StudentModel(TypedDict):
    accuracy: float     # 0.0–1.0
    attempts: int
    mastered: bool      # accuracy >= 0.75 and attempts >= 3


class TeachingStep(TypedDict):
    step: int
    bridge_concept: str   # concept the student already knows — the on-ramp
    target: str           # what this step is trying to unlock
    question: str         # the Socratic question to ask
    why: str              # internal reasoning (not shown to student)


class SessionPlan(TypedDict):
    target_concept: str
    goal: str                       # one sentence: what mastery looks like
    teaching_chain: list[TeachingStep]
    current_step: int


class TurnEvaluation(TypedDict):
    verdict: str        # "correct" | "acceptable" | "incorrect"
    what_was_right: str
    what_was_wrong: str
    encouragement: str  # warm, short — fed to conversationalist


class TutorState(TypedDict):
    messages: list              # [{"role": "user"|"assistant", "content": str}]
    user_id: str
    student_model: dict         # concept_name → StudentModel
    session_plan: SessionPlan
    last_evaluation: TurnEvaluation


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _fetch_concept_stats(user_id: str, db: Session) -> dict:
    """Return concept_name → StudentModel for every concept the user has tried."""
    rows = db.execute(
        select(
            Concept.name,
            func.count(Attempt.id).label("total"),
            func.count(Attempt.id).filter(
                Attempt.evaluation_state.in_(["correct", "acceptable"])
            ).label("correct"),
        )
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .join(Attempt, Attempt.question_id == QuestionConcept.question_id)
        .where(Attempt.user_id == user_id)
        .group_by(Concept.name)
        .having(func.count(Attempt.id) > 0)
    ).all()

    model: dict = {}
    for r in rows:
        accuracy = round((r.correct or 0) / r.total, 2)
        model[r.name] = StudentModel(
            accuracy=accuracy,
            attempts=r.total,
            mastered=(accuracy >= 0.75 and r.total >= 3),
        )
    return model


def _completed_track_ids(user_id: str, db: Session) -> list[int]:
    return db.execute(
        select(UserTrackProgress.track_id).where(
            UserTrackProgress.user_id == user_id,
            UserTrackProgress.completed == True,
        )
    ).scalars().all()


def _max_completed_track_number(user_id: str, db: Session) -> int:
    """Return the highest track number the user has completed (0 if none)."""
    from app.models import Track
    completed_ids = _completed_track_ids(user_id, db)
    if not completed_ids:
        return 0
    result = db.execute(
        select(func.max(Track.number)).where(Track.id.in_(completed_ids))
    ).scalar()
    return result or 0


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------

def _claude(system: str, user: str, max_tokens: int = 512) -> str:
    """Single-turn call — planner and evaluator."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def _claude_chat(system: str, messages: list, max_tokens: int = 512) -> str:
    """Multi-turn call — conversationalist. Passes real message history."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    # Anthropic requires messages to alternate roles; ensure we start with user
    filtered = []
    for m in messages:
        if m["role"] in ("user", "assistant"):
            filtered.append({"role": m["role"], "content": m["content"]})
    if not filtered or filtered[0]["role"] != "user":
        filtered.insert(0, {"role": "user", "content": "Begin."})
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system,
        messages=filtered,
    )
    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def build_graph(checkpointer, db: Session):

    # ── entry router ────────────────────────────────────────────────────────
    def entry_router(state: TutorState) -> str:
        plan = state.get("session_plan")
        msgs = state.get("messages", [])

        if not plan or not plan.get("teaching_chain"):
            return "build_student_model"

        if msgs and msgs[-1]["role"] == "user":
            return "evaluate_turn"

        return "converse"

    # ── build_student_model ─────────────────────────────────────────────────
    def build_student_model(state: TutorState) -> TutorState:
        model = _fetch_concept_stats(state["user_id"], db)
        return {**state, "student_model": model}

    # ── plan_session ────────────────────────────────────────────────────────
    def plan_session(state: TutorState) -> TutorState:
        model: dict = state.get("student_model", {})

        # Only consider concepts introduced up to the student's highest completed track
        max_track = _max_completed_track_number(state["user_id"], db)
        available_concepts: set[str] = set(
            db.execute(
                select(Concept.name).where(Concept.first_track <= max_track)
            ).scalars().all()
        ) if max_track > 0 else set()

        # Split into weak (needs work) and known (can build from)
        # — constrained to concepts the student has actually been exposed to
        weak = {
            name: m for name, m in model.items()
            if not m["mastered"] and m["attempts"] >= 1
            and (not available_concepts or name in available_concepts)
        }
        known = {
            name: m for name, m in model.items()
            if m["mastered"]
        }

        # If nothing attempted yet, prime with the earliest available concept
        if not weak:
            weak = {"present tense verbs": {"accuracy": 0.0, "attempts": 0, "mastered": False}}

        # Sort weak by accuracy ascending — pick the weakest
        target_concept = min(weak, key=lambda n: weak[n]["accuracy"])

        known_summary = (
            ", ".join(f"{n} ({round(m['accuracy']*100)}%)" for n, m in sorted(
                known.items(), key=lambda x: -x[1]["accuracy"]
            )[:10])
            or "none yet"
        )
        weak_summary = (
            ", ".join(f"{n} ({round(m['accuracy']*100)}%)" for n, m in sorted(
                weak.items(), key=lambda x: x[1]["accuracy"]
            )[:10])
        )

        system = """You are designing a Language Transfer style tutoring session.

THE MOST IMPORTANT RULE: Every question must ask the student to PRODUCE a Spanish word or phrase.
Never ask about grammar concepts, never ask "what do we call this?", never ask comprehension
questions in English. The student should always be saying or completing Spanish.

Language Transfer question patterns (use these):
  - "How would you say '___' in Spanish?"
  - "What would you change about '___ ' to make it mean '___'?"
  - "If [known word] means X, how would you say Y?"
  - "Try saying the whole sentence: '___'"

BAD questions (never use):
  - "Who does 'him' refer to — you or someone else?"
  - "Are they the same person or different people?"
  - "What do we call this type of pronoun?"
  - Any question answered with a grammar term or English explanation

Build a chain of 3-5 steps. Each step starts simple (something they can definitely produce)
and builds up to the target concept. The final step should produce the exact Spanish
construction that demonstrates the target concept.

Return ONLY valid JSON, no prose:
{
  "target_concept": "...",
  "goal": "student can produce a Spanish sentence using this concept",
  "teaching_chain": [
    {
      "step": 1,
      "bridge_concept": "what they already know that this builds on",
      "target": "what Spanish production this step unlocks",
      "question": "How would you say '___' in Spanish?",
      "why": "why this step leads toward the target"
    }
  ]
}"""

        user = (
            f"Student level: has completed tracks 1–{max_track} of Language Transfer Complete Spanish.\n"
            f"Target concept to teach: {target_concept}\n"
            f"Concepts the student has mastered: {known_summary}\n"
            f"Concepts the student is weak on: {weak_summary}\n\n"
            "Build a teaching chain appropriate for this level. "
            "Early tracks (1-10) cover: basic verb conjugation (-ar/-er/-ir), "
            "pronouns (yo/tú/él), negation (no), simple questions, want/need/can. "
            "Do not introduce concepts beyond what appears in the completed tracks."
        )

        raw = _claude(system, user, max_tokens=1024)

        # Parse JSON — fall back to a minimal plan if the model misbehaves
        try:
            # Strip markdown code fences if present
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            plan_data = json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            plan_data = {
                "target_concept": target_concept,
                "goal": f"Student can correctly use {target_concept}",
                "teaching_chain": [{
                    "step": 1,
                    "bridge_concept": "prior knowledge",
                    "target": target_concept,
                    "question": f"How would you express something using {target_concept} in Spanish?",
                    "why": "fallback — JSON parse failed",
                }],
            }

        plan: SessionPlan = {
            "target_concept": plan_data["target_concept"],
            "goal": plan_data.get("goal", ""),
            "teaching_chain": plan_data.get("teaching_chain", []),
            "current_step": 0,
        }

        return {**state, "session_plan": plan}

    # ── evaluate_turn ───────────────────────────────────────────────────────
    def evaluate_turn(state: TutorState) -> TutorState:
        msgs = state.get("messages", [])
        plan: SessionPlan = state.get("session_plan", {})
        chain = plan.get("teaching_chain", [])
        step_idx = plan.get("current_step", 0)
        current_step = chain[step_idx] if step_idx < len(chain) else {}

        last_user = next(
            (m["content"] for m in reversed(msgs) if m["role"] == "user"), ""
        )

        system = (
            "You are evaluating a student's Spanish production in a Language Transfer tutoring session. "
            "The student was asked to produce a Spanish word or phrase. "
            "Be lenient: accept missing accents, clitic attachment variants (publicar lo = publicarlo), "
            "minor word-order differences, typos. Only mark incorrect if the Spanish meaning is clearly wrong. "
            "If the student said something in English or off-topic, mark incorrect. "
            "Return JSON only:\n"
            '{"verdict": "correct|acceptable|incorrect", '
            '"what_was_right": "brief note on what Spanish they got right", '
            '"what_was_wrong": "brief note on what Spanish was wrong or missing", '
            '"encouragement": "warm 1-sentence reaction, never reveal the answer"}'
        )
        user = (
            f"Step goal: {current_step.get('target', '')}\n"
            f"Question asked: {current_step.get('question', '')}\n"
            f"Student answered: {last_user}"
        )

        raw = _claude(system, user, max_tokens=256)
        try:
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            ev = json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            verdict = "incorrect"
            ev = {
                "verdict": verdict,
                "what_was_right": "",
                "what_was_wrong": "Could not parse your answer",
                "encouragement": "Give it another try!",
            }

        evaluation = TurnEvaluation(
            verdict=ev.get("verdict", "incorrect"),
            what_was_right=ev.get("what_was_right", ""),
            what_was_wrong=ev.get("what_was_wrong", ""),
            encouragement=ev.get("encouragement", ""),
        )
        return {**state, "last_evaluation": evaluation}

    # ── advance_or_stay router ──────────────────────────────────────────────
    def advance_or_stay(state: TutorState) -> str:
        ev: TurnEvaluation = state.get("last_evaluation", {})
        if ev.get("verdict") in ("correct", "acceptable"):
            return "advance"
        return "stay"

    # ── advance_step ────────────────────────────────────────────────────────
    def advance_step(state: TutorState) -> TutorState:
        plan: SessionPlan = state.get("session_plan", {})
        chain = plan.get("teaching_chain", [])
        current = plan.get("current_step", 0)
        next_step = min(current + 1, len(chain) - 1)
        return {
            **state,
            "session_plan": {**plan, "current_step": next_step},
        }

    # ── converse ────────────────────────────────────────────────────────────
    def converse(state: TutorState) -> TutorState:
        msgs = state.get("messages", [])
        plan: SessionPlan = state.get("session_plan", {})
        chain = plan.get("teaching_chain", [])
        step_idx = plan.get("current_step", 0)
        current_step = chain[step_idx] if step_idx < len(chain) else {}
        ev: TurnEvaluation = state.get("last_evaluation") or {}
        is_final_step = step_idx == len(chain) - 1

        system = """You are a Spanish tutor in the spirit of Michel Thomas / Language Transfer.

THE ONLY RULE THAT MATTERS: Always ask the student to produce Spanish.
Every response ends with a question like "How would you say '___'?" or "Try saying '___' in Spanish."
Never ask comprehension questions in English. Never ask about grammar concepts.
Never ask "who does X refer to?" or "are they the same person?" — these are not LT-style.

The student should always be attempting to say or complete a Spanish word/phrase.
Warm, short (1-3 sentences), always ends with a Spanish production question."""

        # Build the context block for this turn
        context_parts = [
            f"Teaching goal: {plan.get('goal', '')}",
            f"Current step: {current_step.get('question', '')}",
            f"Bridge concept (what they know): {current_step.get('bridge_concept', '')}",
            f"What this step unlocks: {current_step.get('target', '')}",
        ]

        if ev.get("verdict"):
            context_parts += [
                f"Student's last answer was: {ev['verdict']}",
                f"What was right: {ev.get('what_was_right', '')}",
                f"What was wrong: {ev.get('what_was_wrong', '')}",
                f"Encouragement to weave in: {ev.get('encouragement', '')}",
            ]
            if ev["verdict"] in ("correct", "acceptable") and is_final_step:
                context_parts.append(
                    "The student has completed the teaching chain. "
                    "Celebrate warmly and ask if they want to explore further or try something new."
                )
            elif ev["verdict"] in ("correct", "acceptable"):
                context_parts.append(
                    "They got it — acknowledge it briefly and ask the NEXT step's question."
                )
            else:
                context_parts.append(
                    "They didn't get it — do NOT repeat the same question. "
                    "Ask a simpler version that approaches the answer from a different angle."
                )
        else:
            context_parts.append(
                "This is the opening of the session. Start warmly and ask the first question."
            )

        # Inject session context into the system prompt — NOT as a user message
        full_system = system + "\n\n--- SESSION CONTEXT ---\n" + "\n".join(context_parts)

        # Pass the real conversation history as proper messages
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in msgs[-8:]  # last 8 messages for context window hygiene
        ]

        ai_text = _claude_chat(full_system, history, max_tokens=256)

        return {
            **state,
            "messages": msgs + [{"role": "assistant", "content": ai_text}],
            "last_evaluation": {},  # clear after each response
        }

    # ── assemble graph ──────────────────────────────────────────────────────
    graph = StateGraph(TutorState)

    graph.add_node("build_student_model", build_student_model)
    graph.add_node("plan_session", plan_session)
    graph.add_node("evaluate_turn", evaluate_turn)
    graph.add_node("advance_step", advance_step)
    graph.add_node("converse", converse)

    graph.add_conditional_edges(START, entry_router, {
        "build_student_model": "build_student_model",
        "evaluate_turn": "evaluate_turn",
        "converse": "converse",
    })

    graph.add_edge("build_student_model", "plan_session")
    graph.add_edge("plan_session", "converse")
    graph.add_edge("converse", END)

    graph.add_conditional_edges("evaluate_turn", advance_or_stay, {
        "advance": "advance_step",
        "stay": "converse",
    })
    graph.add_edge("advance_step", "converse")

    return graph.compile(checkpointer=checkpointer)
