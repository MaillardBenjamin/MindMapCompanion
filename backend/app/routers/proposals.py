from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.enums import ProposalStatus
from app.models.proposal import Proposal
from app.schemas.proposal import ProposalListOut, ProposalOut
from app.services.proposals import apply_proposal

router = APIRouter(
    prefix="/proposals", tags=["proposals"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=ProposalListOut)
async def list_proposals(
    status: ProposalStatus | None = None,
    node_id: str | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> ProposalListOut:
    query = select(Proposal)
    if status:
        query = query.where(Proposal.status == status)
    if node_id:
        query = query.where(Proposal.node_id == node_id)
    result = await session.execute(query)
    proposals = [ProposalOut.model_validate(p) for p in result.scalars().all()]
    return ProposalListOut(proposals=proposals)


@router.post("/{proposal_id}/approve_and_apply", response_model=ProposalOut)
async def approve_and_apply(
    proposal_id: str, session: AsyncSession = Depends(get_async_session)
) -> ProposalOut:
    proposal = await session.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal introuvable")
    proposal = await apply_proposal(session, proposal, reviewed_by="user")
    await session.commit()
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/reject", response_model=ProposalOut)
async def reject_proposal(
    proposal_id: str, session: AsyncSession = Depends(get_async_session)
) -> ProposalOut:
    proposal = await session.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal introuvable")
    proposal.status = ProposalStatus.rejected
    await session.commit()
    return ProposalOut.model_validate(proposal)
