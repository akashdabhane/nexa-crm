"""Voice input for the assistant, with the Whisper model replaced by a fake."""

from types import SimpleNamespace

import pytest
from av.error import InvalidDataError

from app.core.config import settings
from app.models import Company, Contact, Lead
from app.services.assistant import speech
from tests.conftest import auth_headers


class FakeWhisper:
    def __init__(self, *texts: str, error: Exception | None = None):
        self.texts = texts
        self.error = error
        self.calls: list[dict] = []

    def transcribe(self, audio, **options):
        self.calls.append({"audio": audio.read(), **options})
        if self.error:
            raise self.error
        return (SimpleNamespace(text=text) for text in self.texts), SimpleNamespace(language="en")


@pytest.fixture
def whisper(monkeypatch):
    def use(*texts: str, error: Exception | None = None) -> FakeWhisper:
        fake = FakeWhisper(*texts, error=error)
        monkeypatch.setattr(speech, "_model", None)
        monkeypatch.setattr(speech, "_load_model", lambda: fake)
        return fake

    return use


def upload(client, user, audio: bytes = b"fake-webm-audio"):
    headers = {**auth_headers(user), "Content-Type": "audio/webm"}
    return client.post("/api/assistant/transcribe", content=audio, headers=headers)


def test_transcribes_with_crm_names_as_hints(client, db, rep, whisper):
    company = Company(name="Khadse Industries")
    db.add_all([company, Lead(name="Priya Shah"), Contact(first_name="Vikram", last_name="Khadse")])
    db.commit()
    fake = whisper(" Give me the phone number", " of Vikram Khadse. ")

    response = upload(client, rep)

    assert response.status_code == 200, response.text
    assert response.json() == {"text": "Give me the phone number of Vikram Khadse."}
    [call] = fake.calls
    assert call["audio"] == b"fake-webm-audio"
    assert call["language"] == settings.whisper_language and call["vad_filter"] is True
    assert set(call["hotwords"].split(", ")) == {"Vikram Khadse", "Priya Shah", "Khadse Industries"}


def test_silence_gives_empty_text(client, rep, whisper):
    whisper()
    assert upload(client, rep).json() == {"text": ""}


def test_hints_stay_within_whisper_prompt_budget(db, monkeypatch):
    db.add_all([Lead(name=f"Lead number {n:03}") for n in range(30)] + [Contact(first_name="Ada")])
    db.commit()
    monkeypatch.setattr(speech, "HOTWORDS_MAX_CHARS", 60)

    hint = speech.crm_vocabulary(db)

    assert len(hint) <= 60 and hint.count("Lead number") == 3 and "Ada" in hint


def test_rejects_bad_uploads(client, rep, whisper, monkeypatch):
    whisper(error=InvalidDataError(1094995529, "Invalid data found when processing input"))
    assert "couldn't be read" in upload(client, rep, b"not audio").json()["detail"]
    assert upload(client, rep, b"").status_code == 400

    monkeypatch.setattr("app.api.routes.assistant.MAX_AUDIO_BYTES", 10)
    assert upload(client, rep, b"x" * 11).status_code == 413


def test_needs_sign_in_and_can_be_turned_off(client, rep, whisper, monkeypatch):
    whisper("hi")
    assert client.post("/api/assistant/transcribe", content=b"audio").status_code == 401

    monkeypatch.setattr(settings, "whisper_model", "")
    response = upload(client, rep)
    assert response.status_code == 503 and "turned off" in response.json()["detail"]


def test_model_load_failure_is_reported(client, rep, monkeypatch):
    def broken():
        raise RuntimeError("no internet")

    monkeypatch.setattr(speech, "_model", None)
    monkeypatch.setattr(speech, "_load_model", broken)
    response = upload(client, rep)
    assert response.status_code == 503 and "couldn't be loaded" in response.json()["detail"]
