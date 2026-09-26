import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.models import Pipeline, PipelineStage
from app.models.enums import StageType

# (name, default probability %, type)
DEFAULT_STAGES = [
    ("New", 10, StageType.OPEN),
    ("Contacted", 20, StageType.OPEN),
    ("Qualified", 40, StageType.OPEN),
    ("Proposal", 60, StageType.OPEN),
    ("Negotiation", 80, StageType.OPEN),
    ("Won", 100, StageType.WON),
    ("Lost", 0, StageType.LOST),
]


def create_default_pipeline(db: Session) -> Pipeline:
    pipeline = Pipeline(name="Sales Pipeline", is_default=True)
    pipeline.stages = [
        PipelineStage(name=name, position=index, probability=probability, stage_type=stage_type)
        for index, (name, probability, stage_type) in enumerate(DEFAULT_STAGES)
    ]
    db.add(pipeline)
    db.flush()
    return pipeline


def get_default_pipeline(db: Session) -> Pipeline:
    """The default pipeline; created on first use so a fresh database just works."""
    pipeline = db.scalar(select(Pipeline).where(Pipeline.is_default.is_(True)))
    return pipeline or create_default_pipeline(db)


def get_pipeline(db: Session, pipeline_id: uuid.UUID | None) -> Pipeline:
    if pipeline_id is None:
        return get_default_pipeline(db)
    pipeline = db.get(Pipeline, pipeline_id)
    if pipeline is None:
        raise bad_request("Pipeline does not exist")
    return pipeline


def get_stage(db: Session, stage_id: uuid.UUID, pipeline_id: uuid.UUID | None = None) -> PipelineStage:
    stage = db.get(PipelineStage, stage_id)
    if stage is None or (pipeline_id is not None and stage.pipeline_id != pipeline_id):
        raise bad_request("Stage does not exist in this pipeline")
    return stage


def first_open_stage(pipeline: Pipeline) -> PipelineStage:
    for stage in pipeline.stages:
        if stage.stage_type == StageType.OPEN:
            return stage
    return pipeline.stages[0]
