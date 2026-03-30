from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import get_password_hash, verify_password, create_access_token
from app.db.mock_db import users_db
from app.models.user import UserInDB
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.core.logger import logger

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate) -> Any:
    # Check if user already exists
    if user_in.email in users_db:
        logger.warning(f"Registration failed: User {user_in.email} already exists")
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists in the system.",
        )
    
    user = UserInDB(
        email=user_in.email,
        name=user_in.name,
        hashed_password=get_password_hash(user_in.password),
    )
    users_db[user_in.email] = user
    logger.info(f"User created: {user.email}")
    return user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    # form_data.username will be the email since we configured Swagger
    user = users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=user.email)
    logger.info(f"User logged in successfully: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}
