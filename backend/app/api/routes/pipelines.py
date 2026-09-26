import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models import Deal, Pipeline, PipelineStage, Profile
from app.models.enums import StageType
from app.schemas.pipeline import PipelineCreate, PipelineRead, StageRead, StageUpdate
from app.services.pipelines import get_default_pipeline
from app.utils.query import get_or_404

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("", response_model=list[PipelineRead])
def list_pipelines(_: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    get_default_pipeline(db)  # make sure at least one pipeline exists
    db.commit()
    return db.scalars(select(Pipeline).order_by(Pipeline.is_default.desc(), Pipeline.name)).all()


@router.post("", response_model=PipelineRead, status_code=status.HTTP_201_CREATED)
def create_pipeline(payload: PipelineCreate, _: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    if not any(stage.stage_type == StageType.OPEN for stage in payload.stages):
        raise bad_request("A pipeline needs at least one open stage")
    get_default_pipeline(db)  # the built-in pipeline always exists and stays the default
    pipeline = Pipeline(name=payload.name, is_default=False)
    pipeline.stages = [
        PipelineStage(position=index, **stage.model_dump()) for index, stage in enumerate(payload.stages)
    ]
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return pipeline


@router.patch("/stages/{stage_id}", response_model=StageRead)
def update_stage(
    stage_id: uuid.UUID,
    payload: StageUpdate,
    _: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Rename a stage or change its default probability (applies to open deals in it)."""
    stage = get_or_404(db, PipelineStage, stage_id, "Stage")
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in data.items():
        setattr(stage, field, value)
    if "probability" in data:
        for deal in db.scalars(select(Deal).where(Deal.stage_id == stage.id)).unique():
            deal.probability = stage.probability
    db.commit()
    return stage
