import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import ProposalStatus


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    node_id: uuid.UUID
    agent_name: str
    proposal_json: dict
    status: ProposalStatus
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class ProposalListOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    proposals: list[ProposalOut]
