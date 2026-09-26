from fastapi import APIRouter

from app.api.routes import (
    activities,
    audit_logs,
    companies,
    contacts,
    deals,
    health,
    leads,
    notes,
    notifications,
    pipelines,
    reports,
    tasks,
    timeline,
    users,
)

api_router = APIRouter(prefix="/api")
ROUTERS = (
    health,
    users,
    companies,
    contacts,
    leads,
    pipelines,
    deals,
    activities,
    notes,
    tasks,
    timeline,
    reports,
    notifications,
    audit_logs,
)
for module in ROUTERS:
    api_router.include_router(module.router)
