"""Serialize M2 mutations across processes, using transaction-scoped PostgreSQL locks."""

from functools import wraps
from inspect import signature

from sqlalchemy import text
from app.models.member2.collection import SensorCollectionState


class CollectionPausedError(ValueError):
    pass


def member2_write(function=None, *, allow_paused=False):
    def decorate(operation):
        parameters = signature(operation)

        @wraps(operation)
        async def transaction(*args, **kwargs):
            bound = parameters.bind(*args, **kwargs)
            session, user_id = bound.arguments["session"], bound.arguments["user_id"]
            try:
                if session.get_bind().dialect.name == "postgresql":
                    # Stable namespace and positive profile ID; hash collision can only
                    # serialize unrelated profiles, never allow concurrent same-profile writes.
                    await session.execute(
                        text(
                            "SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"
                        ),
                        {"identity": f"health-guardian-member2:{user_id}"},
                    )
                state = await session.get(
                    SensorCollectionState, user_id, populate_existing=True
                )
                if not allow_paused and state is not None and state.paused:
                    raise CollectionPausedError(
                        "sensor collection is paused; explicitly resume before syncing"
                    )
                result = await operation(*args, **kwargs)
                await session.commit()
                return result
            except BaseException:
                await session.rollback()
                raise

        return transaction

    return decorate(function) if function is not None else decorate


@member2_write(allow_paused=True)
async def resume_collection(session, user_id: int) -> None:
    state = await session.get(SensorCollectionState, user_id)
    if state is not None:
        state.paused = False
    await session.flush()
