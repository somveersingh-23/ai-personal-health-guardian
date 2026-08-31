"""JWT authentication; production APIs derive user identity only from the token subject."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: int


def create_access_token(user_id: int, settings: Settings, expires_minutes: int | None = None) -> str:
    """Used by the real auth module/test fixtures; Member 2 exposes no token-mint endpoint."""

    if user_id <= 0:
        raise ValueError("user_id must be positive")
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=expires_minutes or settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    app_settings: Settings = request.app.state.settings
    try:
        claims = jwt.decode(
            credentials.credentials,
            app_settings.jwt_secret,
            algorithms=[app_settings.jwt_algorithm],
            issuer=app_settings.jwt_issuer,
            audience=app_settings.jwt_audience,
            options={"require": ["sub", "iss", "aud", "iat", "nbf", "exp"]},
        )
        user_id = int(claims["sub"])
        if user_id <= 0:
            raise ValueError
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return AuthenticatedUser(user_id=user_id)
