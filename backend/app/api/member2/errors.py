"""Translate expected M2 domain errors without changing shared application handlers."""

from fastapi import HTTPException
from fastapi.routing import APIRoute
from sqlalchemy.exc import IntegrityError
from app.services.sensors.transactions import CollectionPausedError


class Member2Route(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request):
            try:
                return await handler(request)
            except CollectionPausedError as exc:
                raise HTTPException(409, str(exc)) from exc
            except IntegrityError as exc:
                raise HTTPException(
                    409, "sensor identity conflicts with an existing record"
                ) from exc
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc

        return handle
