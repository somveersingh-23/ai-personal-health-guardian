from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Member3Identity:
    user_id: str


def _decode(token: str) -> Member3Identity:
    secret = os.environ.get("MEMBER3_JWT_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Member 3 JWT secret is not configured")
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=os.environ.get("MEMBER3_JWT_AUDIENCE", "health-guardian-mobile"),
            issuer=os.environ.get("MEMBER3_JWT_ISSUER", "health-guardian"),
            options={"require": ["sub", "exp", "iat", "aud", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token") from exc
    user_id = str(claims.get("sub", "")).strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token has no subject")
    return Member3Identity(user_id)


async def require_member3_identity(request: Request) -> Member3Identity:
    # Delivery providers authenticate the narrowly scoped callback with the
    # fail-closed webhook secret in notifications.provider_callback. They do
    # not possess an end-user JWT.
    endpoint = request.scope.get("endpoint")
    if getattr(endpoint, "__name__", "") == "provider_callback":
        return Member3Identity("notification-provider")

    credentials: HTTPAuthorizationCredentials | None = await _bearer(request)
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    identity = _decode(credentials.credentials)
    requested_user = request.query_params.get("user_id")
    if requested_user is None and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        try:
            payload = await request.json()
            if isinstance(payload, dict):
                requested_user = payload.get("user_id")
        except (ValueError, RuntimeError):
            requested_user = None
    if requested_user is not None and str(requested_user).strip() != identity.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user's Member 3 data")
    request.state.member3_identity = identity
    return identity


def member3_identity_from_request(request: Request) -> Member3Identity:
    """Return the identity established by the router-level JWT dependency.

    Resource-ID routes cannot infer ownership from a path parameter. They use
    the authenticated subject rather than an owner ID supplied by the caller.
    """
    identity = getattr(request.state, "member3_identity", None)
    if not isinstance(identity, Member3Identity):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated Member 3 identity required",
        )
    return identity


def member3_identity_if_authenticated(request: Request) -> Member3Identity | None:
    """Read the router-authenticated identity when hosted by the shared API.

    The standalone Member 3 factory intentionally has no production auth
    middleware and is retained only for isolated unit tests and local demos.
    """
    identity = getattr(request.state, "member3_identity", None)
    return identity if isinstance(identity, Member3Identity) else None
