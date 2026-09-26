"""Deal business logic shared by the deals API and lead conversion."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.models import Company, Contact, Deal, PipelineStage, Profile
from app.models.enums import StageType
from app.services import pipelines


def validate_links(db: Session, company_id: uuid.UUID | None, contact_id: uuid.UUID | None) -> None:
    if company_id is not None and db.get(Company, company_id) is None:
        raise bad_request("Company does not exist")
    if contact_id is not None and db.get(Contact, contact_id) is None:
        raise bad_request("Contact does not exist")


def apply_stage(deal: Deal, stage: PipelineStage) -> None:
    """Put a deal in a stage: status, probability and closed_at follow the stage."""
    deal.stage = stage
    deal.stage_id = stage.id
    deal.pipeline_id = stage.pipeline_id
    deal.status = stage.stage_type
    deal.probability = stage.probability
    if stage.stage_type == StageType.OPEN:
        deal.closed_at = None
    elif deal.closed_at is None:
        deal.closed_at = datetime.now(UTC)


def create_deal(
    db: Session,
    *,
    user: Profile,
    owner_id: uuid.UUID,
    name: str,
    value: Decimal = Decimal(0),
    currency: str = "USD",
    pipeline_id: uuid.UUID | None = None,
    stage_id: uuid.UUID | None = None,
    probability: int | None = None,
    expected_close_date: date | None = None,
    company_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None,
    description: str | None = None,
) -> Deal:
    validate_links(db, company_id, contact_id)
    pipeline = pipelines.get_pipeline(db, pipeline_id)
    stage = (
        pipelines.get_stage(db, stage_id, pipeline.id) if stage_id else pipelines.first_open_stage(pipeline)
    )
    deal = Deal(
        name=name,
        value=value,
        currency=currency,
        expected_close_date=expected_close_date,
        company_id=company_id,
        contact_id=contact_id,
        owner_id=owner_id,
        created_by_id=user.id,
        description=description,
    )
    apply_stage(deal, stage)
    if probability is not None:
        deal.probability = probability
    db.add(deal)
    db.flush()
    return deal
