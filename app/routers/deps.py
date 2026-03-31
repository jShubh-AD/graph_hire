"""
FastAPI dependency — resolves current user from bearer JWT via TigerGraph.
JWT sub = userId (the TigerGraph vertex primary key).
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.config import settings
from app.core.logger import logger
from app.db.tigergraph import get_tg_connection
from app.schemas.token import TokenPayload

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Decode JWT → userId → fetch User vertex from TigerGraph."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user_id = token_data.sub
    try:
        conn = get_tg_connection()
        results = conn.getVertices("User", select="userId,name,email,bio", limit=1,
                                   where=f'userId=="{user_id}"')
        if not results:
            raise HTTPException(status_code=404, detail="User not found")
        return results[0]["attributes"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id} from TG: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch user from graph database")
