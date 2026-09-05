from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.base import Base
from app.database.database import engine

from app.models.member1.health_profile import HealthProfile
from app.api.member1.health_profile import router as health_profile_router


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


@app.get("/")
async def root():

    return {
        "project": "AI Personal Health Guardian",
        "module": "Member 1 - Personal Health Digital Twin",
        "status": "running",
    }