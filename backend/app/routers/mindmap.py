from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.edge import Edge
from app.models.node import Node
from app.schemas.node import MindmapOut, NodeOut, MindmapEdgeOut

router = APIRouter(prefix="/mindmap", tags=["mindmap"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=MindmapOut)
async def get_mindmap(session: AsyncSession = Depends(get_async_session)) -> MindmapOut:
    nodes_result = await session.execute(select(Node))
    edges_result = await session.execute(select(Edge))
    nodes = [NodeOut.model_validate(n) for n in nodes_result.scalars().all()]
    edges = [MindmapEdgeOut.model_validate(e) for e in edges_result.scalars().all()]
    return MindmapOut(nodes=nodes, edges=edges)
