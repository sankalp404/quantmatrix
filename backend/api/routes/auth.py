"""
QuantMatrix V1 - Authentication Routes
=====================================

User authentication, registration, and session management.
Includes JWT token handling and user profile management.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt
import logging

from backend.database import get_db
from backend.models.user import User
from backend.config import settings
from fastapi.responses import RedirectResponse
import httpx

logger = logging.getLogger(__name__)

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = getattr(settings, "SECRET_KEY", "fallback-secret-key-for-development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()


# Schwab OAuth scaffolding
@router.get("/schwab/login")
async def schwab_login():
    if not settings.SCHWAB_CLIENT_ID or not settings.SCHWAB_REDIRECT_URI:
        raise HTTPException(status_code=400, detail="Schwab OAuth not configured")
    auth_url = (
        "https://api.schwab.com/oauth/authorize?response_type=code"
        f"&client_id={settings.SCHWAB_CLIENT_ID}"
        f"&redirect_uri={settings.SCHWAB_REDIRECT_URI}"
        "&scope=read,trade"
    )
    return RedirectResponse(url=auth_url)


@router.get("/schwab/callback")
async def schwab_callback(code: str):
    if (
        not settings.SCHWAB_CLIENT_ID
        or not settings.SCHWAB_CLIENT_SECRET
        or not settings.SCHWAB_REDIRECT_URI
    ):
        raise HTTPException(status_code=400, detail="Schwab OAuth not configured")
    # Exchange code for tokens (placeholder; real endpoints/params required)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token = await client.post(
                "https://api.schwab.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.SCHWAB_REDIRECT_URI,
                    "client_id": settings.SCHWAB_CLIENT_ID,
                    "client_secret": settings.SCHWAB_CLIENT_SECRET,
                },
            )
            if token.status_code >= 400:
                raise HTTPException(
                    status_code=token.status_code, detail="Schwab token exchange failed"
                )
            return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Pydantic models for request/response
class UserCreate(BaseModel):
    """User registration request."""

    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request."""

    username: str
    password: str


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str


class UserResponse(BaseModel):
    """User information response."""

    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Authentication helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the username."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.PyJWTError:
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user.
    Validates JWT token and returns the user object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract token from Authorization header
        token = credentials.credentials
        username = verify_token(token)
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Authentication routes
@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate, db: Session = Depends(get_db)
) -> UserResponse:
    """
    Register a new user.
    Creates a new user account with hashed password.
    """
    # Check if user already exists
    existing_user = (
        db.query(User)
        .filter((User.username == user_data.username) | (User.email == user_data.email))
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info(f"New user registered: {user_data.username}")

    return UserResponse.from_orm(db_user)


@router.post("/login", response_model=Token)
async def login_user(user_data: UserLogin, db: Session = Depends(get_db)) -> Token:
    """
    Authenticate user and return JWT token.
    """
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {user.username}")

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user)) -> UserResponse:
    """
    Get current user information.
    Requires valid authentication token.
    """
    return UserResponse.from_orm(user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Update current user information.
    Requires valid authentication token.
    """
    # Update allowed fields
    allowed_fields = ["full_name", "email"]
    for field, value in user_update.items():
        if field in allowed_fields and hasattr(current_user, field):
            setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    logger.info(f"User updated: {current_user.username}")

    return UserResponse.from_orm(current_user)


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change user password.
    Requires valid authentication token and current password.
    """
    # Verify current password
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    # Update password
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()

    logger.info(f"Password changed for user: {current_user.username}")

    return {"message": "Password updated successfully"}


@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_user)):
    """
    Logout user (token invalidation would be handled client-side).
    """
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Successfully logged out"}


# Health check endpoint
@router.get("/health")
async def auth_health_check():
    """Health check for authentication service."""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
    }
