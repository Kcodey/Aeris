from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session
from aeris.services.auth_service import AuthService
from aeris.utils.security import verify_token

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: int
    username: str


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    username: str = payload.get("username")
    if user_id is None or username is None:
        raise credentials_exception
    return TokenData(user_id=int(user_id), username=username)


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Register a new user."""
    service = AuthService(session)

    # Check if user exists
    existing_user = await service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    user = await service.create_user(user_data.username, user_data.password)
    return UserResponse(id=user.id, username=user.username, is_active=user.is_active)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Login and get access token."""
    service = AuthService(session)
    user = await service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = service.create_access_token_for_user(user)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get current user info."""
    service = AuthService(session)
    user = await service.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(id=user.id, username=user.username, is_active=user.is_active)
