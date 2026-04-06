"""
Routes REST pour les agents IA.

Expose les agents via des endpoints REST sécurisés:
- POST /api/agents/mindmap/organize: Organise du texte dans le mindmap
- POST /api/agents/mindmap/reorganize: Réorganise la structure du mindmap
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.crud.mindmap import get_mindmap
from app.agents.mindmap_organizer import mindmap_organizer
from app.agents.mindmap_reorganizer import mindmap_reorganizer
from app.agents.github_security_audit import github_security_audit_agent


router = APIRouter(prefix="/agents", tags=["Agents IA"])


# === Schémas de requête ===

class OrganizeRequest(BaseModel):
    """Requête pour organiser du texte dans le mindmap"""
    mindmap_id: int
    text: str
    auto_apply: bool = True


class ReorganizeRequest(BaseModel):
    """Requête pour réorganiser le mindmap"""
    mindmap_id: int
    auto_apply: bool = True
    focus_area: Optional[str] = None


class GitHubSecurityAuditRequest(BaseModel):
    """Requête pour auditer le dernier commit d'un dépôt GitHub"""

    owner: str
    repo: str
    branch: str = "main"
    extra_context: Optional[str] = None


class AgentListItem(BaseModel):
    """Information sur un agent"""
    name: str
    description: str
    endpoint: str
    method: str = "POST"


# === Endpoints ===

@router.get("/", response_model=list[AgentListItem])
async def list_agents():
    """Liste tous les agents disponibles"""
    return [
        AgentListItem(
            name=mindmap_organizer.name,
            description=mindmap_organizer.description,
            endpoint="/api/agents/mindmap/organize",
        ),
        AgentListItem(
            name=mindmap_reorganizer.name,
            description=mindmap_reorganizer.description,
            endpoint="/api/agents/mindmap/reorganize",
        ),
        AgentListItem(
            name=github_security_audit_agent.name,
            description=github_security_audit_agent.description,
            endpoint="/api/agents/github/security-audit",
        ),
    ]


@router.post("/mindmap/organize")
async def organize_text(
    request: OrganizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Organise le texte saisi dans le mindmap.
    
    L'agent analyse le texte et:
    - Identifie les thèmes et sous-thèmes
    - Crée ou met à jour des nœuds existants
    - Positionne logiquement le contenu dans la hiérarchie
    
    Args:
        mindmap_id: ID du mindmap cible
        text: Texte à organiser
        auto_apply: Si true, applique automatiquement les suggestions (défaut: true)
    
    Returns:
        Résultat de l'organisation avec les nœuds créés/modifiés
    """
    # Vérifier que le mindmap existe et appartient à l'utilisateur
    mindmap = get_mindmap(db, request.mindmap_id, current_user.id)
    if not mindmap:
        raise HTTPException(
            status_code=404,
            detail="Mindmap non trouvé ou vous n'êtes pas autorisé à y accéder"
        )
    
    if not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Le texte ne peut pas être vide"
        )
    
    # Exécuter l'agent
    result = await mindmap_organizer.execute(
        db=db,
        mindmap_id=request.mindmap_id,
        user_id=current_user.id,
        text=request.text,
        auto_apply=request.auto_apply,
    )
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error or "Erreur lors de l'exécution de l'agent"
        )
    
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data,
    }


@router.post("/mindmap/reorganize")
async def reorganize_mindmap(
    request: ReorganizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Réorganise la structure du mindmap.
    
    L'agent analyse la structure existante et propose:
    - Des réorganisations hiérarchiques
    - Des fusions de nœuds similaires
    - Des renommages pour plus de clarté
    - Des suppressions de redondances
    
    Args:
        mindmap_id: ID du mindmap cible
        auto_apply: Si true, applique automatiquement les actions (défaut: true)
        focus_area: Zone spécifique à optimiser (optionnel)
    
    Returns:
        Résultat de la réorganisation avec les actions appliquées
    """
    # Vérifier que le mindmap existe et appartient à l'utilisateur
    mindmap = get_mindmap(db, request.mindmap_id, current_user.id)
    if not mindmap:
        raise HTTPException(
            status_code=404,
            detail="Mindmap non trouvé ou vous n'êtes pas autorisé à y accéder"
        )
    
    # Exécuter l'agent
    result = await mindmap_reorganizer.execute(
        db=db,
        mindmap_id=request.mindmap_id,
        user_id=current_user.id,
        auto_apply=request.auto_apply,
        focus_area=request.focus_area,
    )
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error or "Erreur lors de l'exécution de l'agent"
        )
    
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data,
    }


@router.post("/github/security-audit")
async def github_security_audit(
    request: GitHubSecurityAuditRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Audite le code modifié par le **dernier commit** sur une branche GitHub (API lecture seule).

    Utilise l'outil `fetch_last_commit_diff_for_security_audit` puis un modèle LLM pour l'analyse AppSec.
    Configurez `GITHUB_TOKEN` sur le serveur pour les dépôts privés ou un meilleur quota API.
    """
    if not request.owner.strip() or not request.repo.strip():
        raise HTTPException(
            status_code=400,
            detail="owner et repo sont obligatoires",
        )

    result = await github_security_audit_agent.execute(
        owner=request.owner.strip(),
        repo=request.repo.strip(),
        branch=(request.branch or "main").strip(),
        extra_context=request.extra_context,
    )

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error or "Erreur lors de l'audit de sécurité",
        )

    return {
        "success": result.success,
        "message": result.message,
        "data": result.data,
    }


# === Endpoints futurs (placeholders) ===

@router.post("/cv/match", include_in_schema=False)
async def match_cv_offer():
    """Matching CV / Offre d'emploi (à implémenter)"""
    raise HTTPException(status_code=501, detail="Agent non encore implémenté")


@router.post("/email/respond", include_in_schema=False)
async def respond_email():
    """Automatisation de réponse email (à implémenter)"""
    raise HTTPException(status_code=501, detail="Agent non encore implémenté")


@router.post("/reminder/create", include_in_schema=False)
async def create_reminder():
    """Création de rappels intelligents (à implémenter)"""
    raise HTTPException(status_code=501, detail="Agent non encore implémenté")


@router.post("/article/write", include_in_schema=False)
async def write_article():
    """Rédaction d'article (à implémenter)"""
    raise HTTPException(status_code=501, detail="Agent non encore implémenté")
