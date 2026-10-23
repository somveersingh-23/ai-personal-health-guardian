from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.base import Base
from app.database.database import engine

# Import every Member 1 model before create_all so metadata is complete.
from app.models.member1.health_event import HealthEvent  # noqa: F401
from app.models.member1.health_profile import HealthProfile  # noqa: F401
from app.api.member1.health_event import router as health_event_router
from app.api.member1.health_profile import router as health_profile_router
from app.api.member1.health_timeline import router as health_timeline_router
from app.api.member1.health_intelligence import router as health_intelligence_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all is convenient for this development prototype. Use Alembic
    # migrations before a production deployment.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="AI Personal Health Guardian",
    description=(
        "Member 1 APIs for health profiles, health events, timeline, "
        "personal baselines, Digital Twin state, and data-driven insights."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# Local Android emulator and local development clients can call this API.
# Restrict origins to known hosts before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_profile_router)
app.include_router(health_event_router)
app.include_router(health_timeline_router)
app.include_router(health_intelligence_router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "project": "AI Personal Health Guardian",
        "module": "Member 1 - Personal Health Digital Twin",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
