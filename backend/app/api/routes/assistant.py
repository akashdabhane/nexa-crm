from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models import Profile
from app.schemas.assistant import ChatRequest, ChatResponse, TranscriptionResponse
from app.services import assistant
from app.services.assistant import speech

router = APIRouter(prefix="/assistant", tags=["assistant"])

# A two-minute Opus clip is ~1 MB; this leaves room for less efficient browser codecs.
MAX_AUDIO_BYTES = 10 * 1024 * 1024


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    """Send the conversation; the assistant replies and saves what it learned as CRM records."""
    return assistant.chat(db, user, payload.messages)


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    openapi_extra={"requestBody": {"required": True, "content": {"audio/*": {"schema": {"type": "string"}}}}},
)
async def transcribe(request: Request, _: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    """Turn a voice recording (the raw audio file as the request body) into text for the chat box."""
    audio = bytearray()
    async for chunk in request.stream():
        audio += chunk
        if len(audio) > MAX_AUDIO_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "The recording is too long. Keep it short.")

    def run() -> str:
        return speech.transcribe(bytes(audio), hotwords=speech.crm_vocabulary(db))

    # Whisper is CPU-bound and the DB session is synchronous: keep both off the event loop.
    return {"text": await run_in_threadpool(run)}
