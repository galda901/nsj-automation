from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.routers import applications, candidates, dev, health, ingestion, jobs, matching
from recruitment.config import get_settings
from recruitment.database import create_db_and_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/applications", tags=["applications"])
app.include_router(matching.router, prefix="/matching", tags=["matching"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
app.include_router(dev.router, prefix="/dev", tags=["dev"])
