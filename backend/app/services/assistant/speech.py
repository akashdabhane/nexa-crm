"""Speech-to-text for the assistant's voice input, with open-source Whisper (faster-whisper) on this server.

The browser records a short clip (WebM/Ogg/MP4), and PyAV inside faster-whisper decodes it. Audio is never stored
or sent anywhere else. The model is loaded once, on first use (downloaded from Hugging Face the very first time).

Whisper is good at everyday words but guesses at unusual names ("Khadse" → "Kodsi"), and a misheard name means the
assistant can't find the record. So the names of the most recently touched contacts, leads and companies are
passed as `hotwords`, which biases the model towards spelling them the way the CRM does.
"""

import io
import logging
import threading

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import bad_request, service_unavailable
from app.models import Company, Contact, Lead

logger = logging.getLogger("nexa_crm")

# Whisper's prompt holds ~220 tokens; a name is ~3-5. Keep well inside it, the rest of the window is for the audio.
HOTWORD_NAMES_PER_TYPE = 20
HOTWORDS_MAX_CHARS = 600

_model = None
_model_lock = threading.Lock()


def _load_model():
    from faster_whisper import WhisperModel  # heavy import, only when voice input is used

    return WhisperModel(
        settings.whisper_model, device=settings.whisper_device, compute_type=settings.whisper_compute_type
    )


def get_model():
    global _model
    if not settings.whisper_model:
        raise service_unavailable("Voice input is turned off on this server (WHISPER_MODEL is empty).")
    with _model_lock:
        if _model is None:
            try:
                _model = _load_model()
            except Exception as exc:  # download failed, unknown model name, no CUDA…
                logger.warning("Couldn't load Whisper model %r: %s", settings.whisper_model, exc)
                raise service_unavailable("The speech-to-text model couldn't be loaded. Please try again later.")
    return _model


def crm_vocabulary(db: Session) -> str:
    """Names from the CRM, most recently updated first, as one comma-separated hint string."""
    contact_name = func.concat_ws(" ", Contact.first_name, Contact.last_name)
    queries = [
        select(contact_name).order_by(Contact.updated_at.desc()),
        select(Lead.name).order_by(Lead.updated_at.desc()),
        select(Company.name).order_by(Company.updated_at.desc()),
    ]
    names: dict[str, None] = {}  # ordered and de-duplicated
    for query in queries:
        names.update(dict.fromkeys(db.scalars(query.limit(HOTWORD_NAMES_PER_TYPE))))
    hint = ""
    for name in names:
        if len(hint) + len(name) + 2 > HOTWORDS_MAX_CHARS:
            break
        hint = f"{hint}, {name}" if hint else name
    return hint


def transcribe(audio: bytes, hotwords: str | None = None) -> str:
    if not audio:
        raise bad_request("The recording is empty.")
    model = get_model()
    from av.error import FFmpegError  # PyAV comes with faster-whisper

    try:
        segments, _info = model.transcribe(
            io.BytesIO(audio),
            language=settings.whisper_language or None,
            vad_filter=True,  # skip silence, which is where Whisper tends to invent text
            hotwords=hotwords or None,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
    except FFmpegError:  # not audio, or a truncated recording
        raise bad_request("The recording couldn't be read. Please try again.")
