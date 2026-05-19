from datetime import timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from meditatio.models.user import User
from meditatio.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, username: str, password: str) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(password)
        user = User(username=username, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    def create_access_token_for_user(self, user: User) -> str:
        """Create access token for user."""
        access_token_expires = timedelta(minutes=30)
        return create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires,
        )
