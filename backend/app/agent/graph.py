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
from typing import Optional, TypedDict

import anthropic
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.concepts import concept_stats, max_completed_track_number, set_chat_score
from app.config import settings
from app.models import Concept


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
    target_concept_id: Optional[int]   # resolved concept id, for progress writeback
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
    target_concept_id: Optional[int]  # seeded from ProgressView "Chat" button
    student_model: dict         # concept_name → StudentModel
    session_plan: SessionPlan
    last_evaluation: TurnEvaluation
    suggest_quiz: bool          # True when chat shows mastery → nudge to quiz
    chat_score: float           # last agent-evaluated chat understanding (0–1)


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
        model = {
            s.name: StudentModel(
                accuracy=s.blended,
                attempts=s.total_attempts,
                mastered=s.mastered,
            )
            for s in concept_stats(state["user_id"], db)
        }
        return {**state, "student_model": model}

    # ── plan_session ────────────────────────────────────────────────────────
    def plan_session(state: TutorState) -> TutorState:
        model: dict = state.get("student_model", {})

        # Only consider concepts introduced up to the student's highest completed track
        max_track = max_completed_track_number(state["user_id"], db)
        available_concepts: set[str] = set(
            db.execute(
                select(Concept.name).where(Concept.first_track <= max_track)
            ).scalars().all()
        ) if max_track > 0 else set()

        # not-yet-mastered concepts the student has actually been exposed to
        weak = {
            name: m for name, m in model.items()
            if not m["mastered"] and m["attempts"] >= 1
            and (not available_concepts or name in available_concepts)
        }
        known = {name: m for name, m in model.items() if m["mastered"]}

        # Pick the target concept ------------------------------------------------
        seeded_id = state.get("target_concept_id")
        if seeded_id:
            # Concept-specific session opened from the progress view
            target_concept = db.execute(
                select(Concept.name).where(Concept.id == seeded_id)
            ).scalar_one_or_none() or "present tense verbs"
            target_concept_id = seeded_id
        elif weak:
            # Start with the concept CLOSEST to mastery — reinforce what's nearly
            # solid rather than ambushing the student with their weakest spot.
            target_concept = max(weak, key=lambda n: weak[n]["accuracy"])
            target_concept_id = db.execute(
                select(Concept.id).where(Concept.name == target_concept)
            ).scalar_one_or_none()
        else:
            # Nothing attempted yet — prime with the earliest concept
            target_concept = "present tense verbs"
            target_concept_id = db.execute(
                select(Concept.id).where(Concept.name == target_concept)
            ).scalar_one_or_none()

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
            "target_concept": target_concept,
            "target_concept_id": target_concept_id,
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
        return {**state, "last_evaluation": evaluation, "suggest_quiz": False}

    # ── advance_or_stay router ──────────────────────────────────────────────
    def advance_or_stay(state: TutorState) -> str:
        ev: TurnEvaluation = state.get("last_evaluation", {})
        if ev.get("verdict") not in ("correct", "acceptable"):
            return "stay"
        plan: SessionPlan = state.get("session_plan", {})
        chain = plan.get("teaching_chain", [])
        if plan.get("current_step", 0) >= len(chain) - 1:
            return "complete"   # finished the final step — assess + nudge to quiz
        return "advance"

    # ── assess_progress ─────────────────────────────────────────────────────
    def assess_progress(state: TutorState) -> TutorState:
        """On chain completion, score chat understanding and write it to the DB."""
        plan: SessionPlan = state.get("session_plan", {})
        concept_id = plan.get("target_concept_id")
        msgs = state.get("messages", [])

        if not concept_id:
            return {**state, "suggest_quiz": True}

        transcript = "\n".join(
            f"{m['role']}: {m['content']}" for m in msgs[-12:]
        )
        system = (
            "You are scoring how well a student demonstrated understanding of a "
            "target Spanish concept during a tutoring chat. Reply with ONLY a "
            "number between 0 and 1 (e.g. 0.8). 0 = no understanding shown, "
            "1 = produced the concept correctly and confidently on their own."
        )
        user = (
            f"Target concept: {plan.get('target_concept', '')}\n\n"
            f"Conversation:\n{transcript}"
        )
        raw = _claude(system, user, max_tokens=8)
        try:
            score = float(raw.strip().split()[0])
        except (ValueError, IndexError):
            score = 0.6

        score = round(min(max(score, 0.0), 1.0), 2)
        set_chat_score(state["user_id"], concept_id, score, db)
        return {**state, "suggest_quiz": True, "chat_score": score}

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

        system = """You're a friend who happens to be great at Spanish, teaching casually over coffee — not a professor.

THE ONLY RULE THAT MATTERS: Always end by asking the student to produce Spanish.
End every reply with something like "How would you say '___'?" or "Try saying '___'."
Never ask comprehension questions in English. Never ask about grammar concepts or terms.
Never ask "who does X refer to?" or "are they the same person?" — that's not the vibe.

Tone: relaxed, encouraging, plain language. Talk like a person, not a textbook.
No jargon, no lecturing. Keep it SHORT — 1-2 sentences, then the question.
The student should always be the one saying or completing the Spanish."""

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
    graph.add_node("assess_progress", assess_progress)
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
        "complete": "assess_progress",
    })
    graph.add_edge("advance_step", "converse")
    graph.add_edge("assess_progress", "converse")

    return graph.compile(checkpointer=checkpointer)
