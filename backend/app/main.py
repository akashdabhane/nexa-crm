import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.router import api_router
from app.core.config import settings
from app.dependencies.auth import ORG_ERROR_HEADER

logger = logging.getLogger("nexa_crm")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "REST API for NexaCRM. Authenticate with a Supabase access token: `Authorization: Bearer <token>`. "
            "CRM endpoints also need `X-Organization-Id: <organization id>` (see GET /api/organizations)."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Lets the browser app read it and send the user back to the organization picker.
        expose_headers=[ORG_ERROR_HEADER],
    )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
        # A constraint the API validation didn't catch (e.g. a race on a unique field).
        logger.warning("Integrity error: %s", exc.orig)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "This change conflicts with existing data."},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        # Log the full error server-side; never leak internals to the client.
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Something went wrong on our side. Please try again."},
        )

    app.include_router(api_router)
    return app


app = create_app()
