from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.action import Action
from app.schemas.action import ActionCreate, ActionListOut, ActionOut, ActionUpdate

router = APIRouter(
    prefix="/actions", tags=["actions"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=ActionListOut)
async def list_actions(
    node_id: str | None = None, session: AsyncSession = Depends(get_async_session)
) -> ActionListOut:
    query = select(Action)
    if node_id:
        query = query.where(Action.node_id == node_id)
    result = await session.execute(query)
    actions = [ActionOut.model_validate(a) for a in result.scalars().all()]
    return ActionListOut(actions=actions)


@router.post("", response_model=ActionOut)
async def create_action(
    payload: ActionCreate, session: AsyncSession = Depends(get_async_session)
) -> ActionOut:
    action = Action(**payload.model_dump())
    session.add(action)
    await session.flush()
    await session.commit()
    return ActionOut.model_validate(action)


@router.patch("/{action_id}", response_model=ActionOut)
async def update_action(
    action_id: str,
    payload: ActionUpdate,
    session: AsyncSession = Depends(get_async_session),
) -> ActionOut:
    action = await session.get(Action, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(action, field, value)
    await session.commit()
    return ActionOut.model_validate(action)


@router.delete("/{action_id}")
async def delete_action(
    action_id: str, session: AsyncSession = Depends(get_async_session)
) -> dict:
    action = await session.get(Action, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action introuvable")
    await session.delete(action)
    await session.commit()
    return {"deleted": True}
