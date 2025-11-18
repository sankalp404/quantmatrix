"""
QuantMatrix V1 - API Dependencies
Common dependencies for API endpoints.
"""

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from backend.database import get_db
from backend.models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user.
    Used by all protected endpoints.
    """
    try:
        _token = credentials.credentials

        # TODO: Implement proper JWT token validation
        # For now, using a placeholder implementation

        # In production, this would:
        # 1. Decode JWT token
        # 2. Verify signature
        # 3. Check expiration
        # 4. Extract user ID

        # Placeholder: assume token contains user ID for testing
        # Replace with proper JWT implementation
        user_id = 1  # This should come from JWT token

        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure current user has admin privileges.
    """
    from backend.models.user import UserRole

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    return current_user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
    db: Session = Depends(get_db),
):
    """Return None if no credentials provided; otherwise validate like get_current_user."""
    if not credentials:
        return None
    try:
        _token = credentials.credentials
        user_id = 1  # TODO: decode from JWT when implemented
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Optional auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
