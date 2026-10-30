"""Member 3 privacy export and purge endpoints."""

from fastapi import APIRouter, Depends, Query
from app.schemas.member3.data_controls import Member3DataExport, Member3PurgeResponse
from app.services.member3.guardian.data_control_service import DataControlService

router = APIRouter(prefix="/api/v1/member3/data", tags=["Member 3 - Data Controls"])


def get_data_control_service() -> DataControlService:
    raise RuntimeError("DataControlService must be injected by the Member 3 app")


@router.get("/export", response_model=Member3DataExport)
async def export_data(user_id: str = Query(min_length=1, max_length=128),
                      service: DataControlService = Depends(get_data_control_service)) -> Member3DataExport:
    return service.export(user_id)


@router.delete("", response_model=Member3PurgeResponse)
async def purge_data(user_id: str = Query(min_length=1, max_length=128),
                     service: DataControlService = Depends(get_data_control_service)) -> Member3PurgeResponse:
    return service.purge(user_id)
