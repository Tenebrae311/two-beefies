"""FastAPI backend: /api/ask, /api/debate (SSE), /api/source/{cite_id}.

Run: uv run uvicorn two_beefies.api:app --reload --port 8000
"""

import asyncio
import json
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from two_beefies import qa, retrieval
from two_beefies.debate import run_debate

app = FastAPI(title="Knowledge Across Time")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


class AskRequest(BaseModel):
    question: str


@app.post("/api/ask")
async def ask(req: AskRequest) -> dict:
    out = await asyncio.to_thread(qa.ask, req.question)
    out.pop("messages", None)
    out["trace"] = [{"name": c["name"], "args": c["args"]} for c in out["trace"]]
    return out


@app.get("/api/debate")
async def debate(topic: str, rounds: int = 3):
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    def emit(event: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def worker() -> None:
        try:
            run_debate(topic, emit, rounds=max(1, min(rounds, 4)))
        except Exception as e:
            emit({"type": "error", "message": f"{type(e).__name__}: {e}"})
            emit({"type": "done"})

    threading.Thread(target=worker, daemon=True).start()

    async def stream():
        while True:
            event = await queue.get()
            yield {"data": json.dumps(event, ensure_ascii=False, default=str)}
            if event["type"] == "done":
                break

    return EventSourceResponse(stream())


@app.get("/api/source/{cite_id}")
async def source(cite_id: str) -> dict:
    try:
        row = await asyncio.to_thread(retrieval.get, cite_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if row is None:
        raise HTTPException(404, f"Unknown citation {cite_id}")
    return retrieval.to_citation(row, full_text=True)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}
