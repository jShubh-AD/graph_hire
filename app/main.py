from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import logger
from app.routers.auth import router as auth_router
from app.routers.user import router as user_router
from app.routers.resume import router as resume_router
from app.routers.jobs import router as jobs_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for AI Job Recommender System"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(resume_router, prefix="/resume", tags=["Resume"])
app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])

@app.on_event("startup")
def startup_event():
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    
@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}
