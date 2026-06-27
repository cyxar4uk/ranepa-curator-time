"""F6: программа тайм-менеджмента (карточки)."""
from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.schemas import TMCardOut, TMCompleteIn
from app.services import tm

router = APIRouter(prefix="/api", tags=["time-management"])


@router.get("/tm", response_model=list[TMCardOut])
async def list_cards(user: CurrentUser, session: SessionDep):
    return await tm.list_cards(session, user)


@router.post("/tm/{card_id}/complete", response_model=TMCardOut)
async def complete_card(
    card_id: int, data: TMCompleteIn, user: CurrentUser, session: SessionDep
) -> TMCardOut:
    return await tm.complete_card(session, user, card_id, data.answer)
