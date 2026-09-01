from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.member1.health_profile import router as health_profile_router
from app.api.member3.app import build_service_container, configure_member3_services
from app.api.member3.registration import register_member3_routers
from app.database.base import Base
from app.database.database import engine
from app.models.member1.health_profile import HealthProfile


@asynccontextmanager
async def lifespan(app: FastAPI):

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


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
# Member 3 has a linked service graph (including data controls).  Configure it
# in the shared host as well as in the standalone development factory.
configure_member3_services(app, build_service_container())


@app.get("/")
async def root():

    return {
        "project": "AI Personal Health Guardian",
        "module": "Member 1 - Personal Health Digital Twin",
        "status": "running",
    }
