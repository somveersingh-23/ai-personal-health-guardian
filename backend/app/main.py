"""FastAPI application factory for the shared health-guardian backend."""

from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.member1.health_profile import router as health_profile_router
from app.api.member2 import preview_router, production_router
from app.api.member3.app import build_service_container, configure_member3_services
from app.api.member3.registration import register_member3_routers
from app.core.config import Settings
from app.core.config import settings as default_settings
from app.database import database as database_module
from app.database.base import Base


class ApiGuardMiddleware(BaseHTTPMiddleware):
    """Bound declared request size and provide a per-process abuse-control backstop."""

    def __init__(self, app: FastAPI, max_request_bytes: int, requests_per_minute: int = 120) -> None:
        super().__init__(app)
        self.max_request_bytes = max_request_bytes
        self.requests_per_minute = requests_per_minute
        self.requests: OrderedDict[str, deque[float]] = OrderedDict()
        self.last_cleanup = monotonic()

    @staticmethod
    def error_response(
        status_code: int,
        detail: str,
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        response = JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_request_bytes:
                    return self.error_response(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="request body exceeds configured maximum",
                    )
            except ValueError:
                return self.error_response(status_code=400, detail="invalid Content-Length")

        if request.method in {"POST", "PUT", "PATCH"}:
            body = await request.body()
            if len(body) > self.max_request_bytes:
                return self.error_response(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="request body exceeds configured maximum",
                )

        if request.url.path.startswith("/api/"):
            client = request.client.host if request.client else "unknown"
            now = monotonic()
            if now - self.last_cleanup >= 60:
                for key, existing in list(self.requests.items()):
                    while existing and existing[0] <= now - 60:
                        existing.popleft()
                    if not existing:
                        del self.requests[key]
                self.last_cleanup = now
            bucket = self.requests.setdefault(client, deque())
            self.requests.move_to_end(client)
            while len(self.requests) > 10_000:
                self.requests.popitem(last=False)
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= self.requests_per_minute:
                return self.error_response(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="rate limit exceeded",
                    headers={"Retry-After": "60"},
                )
            bucket.append(now)

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


def create_app(app_settings: Settings | None = None) -> FastAPI:
    resolved = app_settings or default_settings
    database_module.configure_database(resolved.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Production is migration-only; auto-create exists for local development/tests.
        if resolved.auto_create_schema:
            from app.models.member1.health_profile import HealthProfile  # noqa: F401
            from app.models.member2 import (  # noqa: F401
                ConsentReceipt,
                DeviceCapability,
                DeviceRegistry,
                HealthConnectSyncState,
                HealthEvent,
                RawSensorAudit,
                ReconciliationRecord,
                ReconciliationSession,
                SensorIngestionAudit,
                SourceTombstone,
            )
            from app.models.member3 import Member3GuardianRecord  # noqa: F401

            async with database_module.get_engine().begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        yield
        await database_module.get_engine().dispose()

    application = FastAPI(
        title="AI Personal Health Guardian",
        description=(
            "Privacy-first research/wellness health intelligence. "
            "Member 2 outputs are non-diagnostic evidence, never emergency decisions."
        ),
        version="0.2.0",
        lifespan=lifespan,
    )
    application.state.settings = resolved
    application.add_middleware(ApiGuardMiddleware, max_request_bytes=resolved.max_request_bytes)
    application.include_router(health_profile_router)
    application.include_router(production_router)
    if resolved.enable_preview_endpoints:
        application.include_router(preview_router)
    # Member 3 stays behind its own JWT dependency; the guardian must never
    # use untrusted request data as an authenticated user identity.
    configure_member3_services(application, build_service_container())
    register_member3_routers(application)

    @application.get("/")
    async def root() -> dict[str, object]:
        return {
            "project": "AI Personal Health Guardian",
            "modules": [
                "member1-digital-twin",
                "member2-sensor-intelligence",
                "member3-ai-guardian",
            ],
            "status": "running",
            "non_diagnostic": True,
        }

    @application.get("/healthz", include_in_schema=False)
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
