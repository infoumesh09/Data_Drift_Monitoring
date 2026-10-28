from fastapi import APIRouter

from . import health, overview, pipelines, datasets, drift, experiments, ai

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(overview.router)
api_router.include_router(pipelines.router)
api_router.include_router(datasets.router)
api_router.include_router(drift.router)
api_router.include_router(experiments.router)
api_router.include_router(ai.router)
