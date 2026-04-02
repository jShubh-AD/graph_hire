from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import logger
from app.routers.auth import router as auth_router
from app.routers.user import router as user_router
from app.routers.resume import router as resume_router
from app.routers.jobs import router as jobs_router
from app.routers.graph import router as graph_router
from app.routers.skills import router as skills_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    logger.info(f"TigerGraph → {settings.TG_HOST} / {settings.TG_GRAPH}")
    yield
    # Shutdown (nothing to clean up for now)
    logger.info(f"Shutting down {settings.PROJECT_NAME}.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for GraphHire — AI Job Recommender powered by TigerGraph",
    lifespan=lifespan,
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(resume_router, prefix="/resume", tags=["Resume"])
app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
app.include_router(graph_router, prefix="/graph", tags=["Graph"])
app.include_router(skills_router, prefix="/skills", tags=["Skills"])


@app.get("/", tags=["health"])
def root_health():
    return {"status": "ok", "project": settings.PROJECT_NAME}
