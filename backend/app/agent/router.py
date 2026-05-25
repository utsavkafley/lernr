import asyncio
import json
import uuid
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langgraph.checkpoint.postgres import PostgresSaver

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.agent.graph import build_graph, TutorState
from app.config import settings

router = APIRouter(prefix="/agent", tags=["agent"])


def _pg_conn_str() -> str:
    """Return a plain psycopg2 connection string (strip SQLAlchemy dialect prefix)."""
    url = settings.database_url
    # Replace postgresql+psycopg2:// → postgresql://
    return url.replace("postgresql+psycopg2://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


@router.post("/chat")
async def chat(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    body = await request.json()
    session_id: str = body.get("session_id") or str(uuid.uuid4())
    user_message: str = body.get("message", "").strip()
    concept_id = body.get("concept_id")  # optional — seeds a concept-specific session

    thread_id = f"{current_user.id}:{session_id}"
    config = {"configurable": {"thread_id": thread_id}}

    async def stream():
        # Send session id first so the client can persist it
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        with PostgresSaver.from_conn_string(_pg_conn_str()) as checkpointer:
            checkpointer.setup()
            graph = build_graph(checkpointer, db)

            # Build input state -----------------------------------------------
            checkpoint = checkpointer.get(config)
            if checkpoint:
                # Resume from persisted state
                persisted: TutorState = checkpoint["channel_values"]
                if user_message:
                    input_state: TutorState = {
                        **persisted,
                        "messages": persisted.get("messages", [])
                        + [{"role": "user", "content": user_message}],
                    }
                else:
                    # Client asked for a fresh question without sending an answer
                    input_state = persisted
            else:
                # Brand-new session
                base: TutorState = {
                    "messages": [],
                    "user_id": str(current_user.id),
                    "target_concept_id": concept_id,
                    "student_model": {},
                    "session_plan": {},
                    "last_evaluation": {},
                }
                if user_message:
                    input_state = {
                        **base,
                        "messages": [{"role": "user", "content": user_message}],
                    }
                else:
                    input_state = base

            # Run graph (sync) in a thread so we don't block the event loop
            result: TutorState = await asyncio.to_thread(
                graph.invoke, input_state, config
            )

        # Stream the last assistant message word-by-word --------------------
        messages = result.get("messages", [])
        last_ai = next(
            (m["content"] for m in reversed(messages) if m["role"] == "assistant"),
            None,
        )

        if last_ai:
            for word in last_ai.split(" "):
                yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
                await asyncio.sleep(0.02)  # subtle pacing for a typewriter feel

        plan = result.get("session_plan") or {}
        chain = plan.get("teaching_chain") or []
        current_step = plan.get("current_step", 0)
        total_steps = len(chain)

        done = {
            "type": "done",
            "concept": plan.get("target_concept", ""),
            "concept_id": plan.get("target_concept_id"),
            "evaluation": (result.get("last_evaluation") or {}).get("verdict", ""),
            "step": current_step + 1,
            "total_steps": total_steps,
            "suggest_quiz": bool(result.get("suggest_quiz")),
            "chat_score": result.get("chat_score", 0.0),
        }
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
