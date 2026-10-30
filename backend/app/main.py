import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.member1.health_profile import router as health_profile_router
from app.api.member3.app import build_service_container, configure_member3_services
from app.api.member3.registration import register_member3_routers
from app.database.base import Base
from app.database.database import engine
from app.models.member1.health_profile import HealthProfile  # noqa: F401
from app.models.member3.guardian_record import Member3Base
from app.services.member3.persistence.container import (
    build_persistent_container,
    create_member3_engine,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is not None:
        if isinstance(engine, AsyncEngine):
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
                await connection.run_sync(Member3Base.metadata.create_all)
        else:
            with engine.begin() as connection:
                Base.metadata.create_all(connection)
                Member3Base.metadata.create_all(connection)

    yield

    if engine is not None:
        if isinstance(engine, AsyncEngine):
            await engine.dispose()
        else:
            engine.dispose()


app = FastAPI(
    title="AI Personal Health Guardian",
    description="Privacy-first personal health intelligence system",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(
    health_profile_router
)
register_member3_routers(app)

# Member 3 persistent service configuration:
# Wire persistent services when a database engine or DATABASE_URL is available,
# falling back to in-memory services if no database is configured.
database_url = os.environ.get("DATABASE_URL") or os.environ.get("MEMBER3_DATABASE_URL")
if engine is not None:
    member3_services = build_persistent_container(engine)
elif database_url:
    member3_services = build_persistent_container(create_member3_engine(database_url))
else:
    member3_services = build_service_container()

configure_member3_services(app, member3_services)


@app.get("/")
async def root():

    return {
        "project": "AI Personal Health Guardian",
        "module": "Member 1 - Personal Health Digital Twin",
        "status": "running",
    }
