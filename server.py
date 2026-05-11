from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal, Optional

import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from english_coach import db
from english_coach.config import SERVER_HOST, SERVER_PORT

_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


class FeedbackIn(BaseModel):
    ts: str
    session_id: str
    session_date: str
    language: Literal["ja", "en"]
    original: str
    correction: str
    explanation: Optional[str] = None
    uuid: str


class SummaryIn(BaseModel):
    session_id: str
    ts: str
    body: str


@app.get("/")
def index():
    return FileResponse(_STATIC_DIR / "index.html")


@app.post("/api/feedback")
def post_feedback(data: FeedbackIn):
    db.insert_correction(
        ts=data.ts,
        session_id=data.session_id,
        session_date=data.session_date,
        language=data.language,
        original=data.original,
        correction=data.correction,
        explanation=data.explanation,
        uuid=data.uuid,
    )
    return {"ok": True}


@app.post("/api/summary")
def post_summary(data: SummaryIn):
    db.insert_summary(session_id=data.session_id, ts=data.ts, body=data.body)
    return {"ok": True}


@app.get("/api/latest")
def get_latest(limit: Annotated[int, Query(ge=1, le=500)] = 20):
    return db.get_latest(limit)


@app.patch("/api/corrections/{correction_id}/hidden")
def hide_correction(correction_id: int):
    db.hide_correction(correction_id)
    return {"ok": True}


@app.get("/api/history")
def get_history(
    session_id: Optional[str] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return db.get_history(session_id=session_id, limit=limit, offset=offset)


if __name__ == "__main__":
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
