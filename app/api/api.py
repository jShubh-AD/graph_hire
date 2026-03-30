from fastapi import APIRouter

from app.api.endpoints import auth, user, resume, jobs

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(resume.router, prefix="/resume", tags=["resume"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
