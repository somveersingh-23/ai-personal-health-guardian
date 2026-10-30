"""Member 2 API routers for the M1 local-integration build."""

from app.api.member2.local import router as local_router
from app.api.member2.preview import router as preview_router

__all__ = ["local_router", "preview_router"]
