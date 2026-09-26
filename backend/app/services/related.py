import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.models import Company, Contact, Deal, Lead

_MODELS = {"contact_id": Contact, "company_id": Company, "lead_id": Lead, "deal_id": Deal}


def validate_related(db: Session, data: dict) -> None:
    """Check that every contact/company/lead/deal id in `data` exists."""
    for field, model in _MODELS.items():
        record_id: uuid.UUID | None = data.get(field)
        if record_id is not None and db.get(model, record_id) is None:
            raise bad_request(f"{model.__name__} does not exist")
