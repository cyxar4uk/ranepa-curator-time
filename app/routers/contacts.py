"""F7: контакты кураторов отделения."""
from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.schemas import CuratorOut
from app.services import catalog

router = APIRouter(prefix="/api", tags=["contacts"])


@router.get("/curators", response_model=list[CuratorOut])
async def list_curators(user: CurrentUser, session: SessionDep):
    return await catalog.list_curators(session)
