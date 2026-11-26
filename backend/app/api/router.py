from fastapi import APIRouter

from app.api.routes import (
    activities,
    assistant,
    audit_logs,
    companies,
    contacts,
    deals,
    health,
    integrations,
    leads,
    notes,
    notifications,
    organizations,
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
    organizations,
    companies,
    contacts,
    leads,
    integrations,
    pipelines,
    deals,
    activities,
    notes,
    tasks,
    timeline,
    reports,
    notifications,
    audit_logs,
    assistant,
)
for module in ROUTERS:
    api_router.include_router(module.router)
