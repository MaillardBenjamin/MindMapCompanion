import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.mindmap import (
    NodeCreate,
    NodeUpdate,
    NodeResponse,
    NodeWithChildren,
)
from app.crud import mindmap as crud_mindmap
from app.services.state_changed import fire_state_changed_triggers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


@router.post("", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
def create_node(
    node: NodeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Crée un nouveau nœud (vérifie que le mindmap appartient à l'utilisateur)"""
    # Vérifier que le mindmap appartient à l'utilisateur
    db_mindmap = crud_mindmap.get_mindmap(db, mindmap_id=node.mindmap_id, user_id=current_user.id)
    if not db_mindmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mindmap introuvable"
        )
    
    try:
        db_node = crud_mindmap.create_node(db, node=node)
        return db_node
    except ValueError as e:
        # Erreur de validation (parent_id invalide, cycle, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/mindmap/{mindmap_id}", response_model=List[NodeResponse])
def get_nodes_by_mindmap(
    mindmap_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les nœuds d'un mindmap"""
    # Vérifier que le mindmap appartient à l'utilisateur
    db_mindmap = crud_mindmap.get_mindmap(db, mindmap_id=mindmap_id, user_id=current_user.id)
    if not db_mindmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mindmap introuvable"
        )
    
    nodes = crud_mindmap.get_nodes_by_mindmap(db, mindmap_id=mindmap_id, user_id=current_user.id)
    return nodes


@router.get("/{node_id}", response_model=NodeWithChildren)
def get_node(
    node_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupère un nœud avec ses enfants et triggers"""
    db_node = crud_mindmap.get_node(db, node_id=node_id, user_id=current_user.id)
    if not db_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nœud introuvable"
        )
    
    # Charger les enfants et triggers
    # Récupérer les enfants via une requête explicite (plus sûr que d'utiliser la relation directement)
    all_nodes = crud_mindmap.get_nodes_by_mindmap(db, mindmap_id=db_node.mindmap_id, user_id=current_user.id)
    children = [n for n in all_nodes if n.parent_id == node_id]
    db_node.children = children
    db_node.triggers = list(db_node.triggers) if db_node.triggers else []
    
    return db_node


@router.put("/{node_id}", response_model=NodeResponse)
def update_node(
    node_id: int,
    node_update: NodeUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Met à jour un nœud"""
    old_node = crud_mindmap.get_node(db, node_id=node_id, user_id=current_user.id)
    old_status = old_node.status if old_node else None

    try:
        db_node = crud_mindmap.update_node(
            db, node_id=node_id, user_id=current_user.id, node_update=node_update
        )
        if not db_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nœud introuvable"
            )

        if (
            old_status is not None
            and node_update.status is not None
            and db_node.status != old_status
        ):
            logger.info(
                "[Nodes] Changement de statut détecté sur le nœud %d : %s → %s",
                node_id, old_status, db_node.status,
            )
            background_tasks.add_task(
                fire_state_changed_triggers,
                node_id=node_id,
                old_status=old_status,
                new_status=db_node.status,
            )

        return db_node
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{node_id}", status_code=status.HTTP_200_OK)
def delete_node(
    node_id: int,
    cascade: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Supprime un nœud et gère ses enfants.
    
    Args:
        cascade: Si True, supprime aussi tous les descendants. 
                 Si False (défaut), les rattache au parent du nœud supprimé.
    
    Returns:
        Informations sur la suppression (nœuds supprimés, enfants réassignés)
    """
    result = crud_mindmap.delete_node(
        db, 
        node_id=node_id, 
        user_id=current_user.id,
        cascade_delete=cascade
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Nœud introuvable")
        )
    
    return {
        "message": f"Nœud {node_id} supprimé avec succès",
        "deleted_ids": result["deleted_ids"],
        "reassigned_children": result["reassigned_children"]
    }
