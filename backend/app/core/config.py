"""Environment-backed configuration with production safety checks."""

import os
from dataclasses import dataclass

DEVELOPMENT_SECRET = "development-only-change-before-deploy"
ALLOWED_ENVIRONMENTS = frozenset({"development", "test", "production"})


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean setting: {value!r}")


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./health_guardian.db"
    jwt_secret: str = DEVELOPMENT_SECRET
    jwt_issuer: str = "ai-personal-health-guardian"
    jwt_audience: str = "health-guardian-api"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    enable_preview_endpoints: bool = True
    auto_create_schema: bool = True
    max_request_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if self.environment not in ALLOWED_ENVIRONMENTS:
            raise ValueError(
                f"APP_ENV must be one of {sorted(ALLOWED_ENVIRONMENTS)}, "
                f"got {self.environment!r}"
            )
        if self.jwt_algorithm != "HS256":
            raise ValueError("only HS256 JWT signing is supported")
        if not 1 <= self.access_token_minutes <= 1_440:
            raise ValueError("ACCESS_TOKEN_MINUTES must be between 1 and 1440")
        if not 16_384 <= self.max_request_bytes <= 10_485_760:
            raise ValueError("MAX_REQUEST_BYTES must be between 16384 and 10485760")
        if self.environment == "production":
            if self.jwt_secret == DEVELOPMENT_SECRET or len(self.jwt_secret) < 32:
                raise ValueError("production JWT_SECRET must be a unique value of at least 32 characters")
            if not self.database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("production DATABASE_URL must use postgresql+asyncpg")
            if self.auto_create_schema:
                raise ValueError("production must use migrations; AUTO_CREATE_SCHEMA cannot be enabled")
            if self.enable_preview_endpoints:
                raise ValueError("production cannot enable unauthenticated preview endpoints")

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("APP_ENV", "development").strip().lower()
        return cls(
            environment=environment,
            database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./health_guardian.db"),
            jwt_secret=os.getenv("JWT_SECRET", DEVELOPMENT_SECRET),
            jwt_issuer=os.getenv("JWT_ISSUER", "ai-personal-health-guardian"),
            jwt_audience=os.getenv("JWT_AUDIENCE", "health-guardian-api"),
            access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "30")),
            enable_preview_endpoints=_as_bool(
                os.getenv("ENABLE_PREVIEW_ENDPOINTS"), environment != "production"
            ),
            auto_create_schema=_as_bool(os.getenv("AUTO_CREATE_SCHEMA"), environment != "production"),
            max_request_bytes=int(os.getenv("MAX_REQUEST_BYTES", "1048576")),
        )


settings = Settings.from_env()
