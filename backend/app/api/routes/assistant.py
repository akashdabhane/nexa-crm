from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models import Profile
from app.schemas.assistant import ChatRequest, ChatResponse
from app.services import assistant

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    """Send the conversation; the assistant replies and saves what it learned as CRM records."""
    return assistant.chat(db, user, payload.messages)
