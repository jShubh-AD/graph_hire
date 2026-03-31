"""
Auth router — register and login backed by TigerGraph.
User passwords are stored as bcrypt hashes in the User vertex.
"""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.logger import logger
from app.db.tigergraph import get_tg_connection
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse, UserLogin

router = APIRouter()


def _get_user_by_email(email: str) -> dict | None:
    """Fetch a User vertex from TigerGraph by email attribute."""
    try:
        conn = get_tg_connection()
        results = conn.getVertices("User", where=f'email=="{email}"', limit=1)
        if results:
            return results[0]["attributes"]
        return None
    except Exception as e:
        logger.error(f"TG getVertices error: {e}")
        return None


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate) -> Any:
    existing = _get_user_by_email(user_in.email)
    if existing:
        logger.warning(f"Registration failed: user {user_in.email} already exists")
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists.",
        )

    user_id = str(uuid.uuid4())
    hashed_pw = get_password_hash(user_in.password)

    conn = get_tg_connection()
    conn.upsertVertex(
        "User",
        user_id,
        attributes={
            "userId": user_id,
            "name": user_in.name,
            "email": user_in.email,
            "hashed_password": hashed_pw,
            "bio": "",
            "resume_text": "",
        },
    )
    logger.info(f"User registered: {user_in.email} → {user_id}")
    return {"userId": user_id, "name": user_in.name, "email": user_in.email, "bio": "", "skills": []}


@router.post("/login", response_model=Token)
def login(login_data: UserLogin) -> Any:
    user = _get_user_by_email(login_data.email)
    if not user:
        logger.warning(f"Login failed — user not found: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(login_data.password, user.get("hashed_password", "")):
        logger.warning(f"Login failed — bad password: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # JWT sub = userId (primary key)
    access_token = create_access_token(subject=user["userId"])
    logger.info(f"User logged in: {login_data.email}")
    return {"access_token": access_token, "token_type": "bearer"}
