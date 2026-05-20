import json
import uuid
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langgraph.checkpoint.postgres import PostgresSaver

from app.auth.dependencies import get_current_user
from app.database import get_db, engine
from app.models import User
from app.agent.graph import build_graph

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat")
async def chat(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    body = await request.json()
    session_id = body.get("session_id") or str(uuid.uuid4())
    user_message = body.get("message", "")

    thread_id = f"{current_user.id}:{session_id}"

    checkpointer = PostgresSaver.from_conn_string(str(engine.url))
    checkpointer.setup()
    graph = build_graph(checkpointer, db)

    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "messages": [],
        "target_concept": "",
        "target_question": {},
        "hint_level": 0,
        "user_id": str(current_user.id),
    }

    if user_message:
        checkpoint = checkpointer.get(config)
        if checkpoint:
            current_state = checkpoint["channel_values"]
            current_state["messages"] = current_state.get("messages", []) + [
                {"role": "user", "content": user_message}
            ]
            input_state = current_state
        else:
            input_state = {**initial_state, "messages": [{"role": "user", "content": user_message}]}
    else:
        input_state = initial_state

    async def stream():
        yield f"data: {json.dumps({'session_id': session_id, 'type': 'session'})}\n\n"

        result = graph.invoke(input_state, config=config)

        messages = result.get("messages", [])
        last_ai = next(
            (m["content"] for m in reversed(messages) if m["role"] == "assistant"),
            None,
        )

        if last_ai:
            for word in last_ai.split(" "):
                yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'concept': result.get('target_concept', '')})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
