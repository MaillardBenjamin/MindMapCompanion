from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.mindmap import Mindmap, Node
from app.schemas.mindmap import (
    MindmapCreate,
    MindmapUpdate,
    MindmapResponse,
    MindmapWithNodes,
)
from app.crud import mindmap as crud_mindmap

router = APIRouter(prefix="/api/mindmaps", tags=["mindmaps"])


@router.post("", response_model=MindmapResponse, status_code=status.HTTP_201_CREATED)
def create_mindmap(
    mindmap: MindmapCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Crée un nouveau mindmap pour l'utilisateur connecté"""
    db_mindmap = crud_mindmap.create_mindmap(db, user_id=current_user.id, mindmap=mindmap)
    return db_mindmap


@router.get("", response_model=List[MindmapResponse])
def get_mindmaps(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les mindmaps de l'utilisateur connecté"""
    mindmaps = crud_mindmap.get_mindmaps_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return mindmaps


@router.get("/{mindmap_id}", response_model=MindmapWithNodes)
def get_mindmap(
    mindmap_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupère un mindmap avec ses nœuds"""
    db_mindmap = crud_mindmap.get_mindmap(db, mindmap_id=mindmap_id, user_id=current_user.id)
    if not db_mindmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mindmap introuvable"
        )
    
    # Récupérer tous les nœuds du mindmap
    nodes = crud_mindmap.get_nodes_by_mindmap(db, mindmap_id=mindmap_id, user_id=current_user.id)
    
    # Construire la structure hiérarchique
    nodes_dict = {node.id: node for node in nodes}
    root_nodes = []
    
    # Initialiser children pour chaque nœud et charger les triggers
    for node in nodes:
        # Initialiser children comme liste vide si ce n'est pas déjà fait
        if not hasattr(node, 'children') or node.children is None:
            node.children = []
        # Charger les triggers si disponible
        if hasattr(node, 'triggers'):
            node.triggers = list(node.triggers) if node.triggers else []
    
    # Construire la hiérarchie parent-enfant
    for node in nodes:
        if node.parent_id is None:
            root_nodes.append(node)
        else:
            parent = nodes_dict.get(node.parent_id)
            if parent:
                if not hasattr(parent, 'children'):
                    parent.children = []
                parent.children.append(node)
    
    db_mindmap.nodes = root_nodes
    return db_mindmap


@router.put("/{mindmap_id}", response_model=MindmapResponse)
def update_mindmap(
    mindmap_id: int,
    mindmap_update: MindmapUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Met à jour un mindmap"""
    db_mindmap = crud_mindmap.update_mindmap(
        db, mindmap_id=mindmap_id, user_id=current_user.id, mindmap_update=mindmap_update
    )
    if not db_mindmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mindmap introuvable"
        )
    return db_mindmap


@router.delete("/{mindmap_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mindmap(
    mindmap_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Supprime un mindmap"""
    success = crud_mindmap.delete_mindmap(db, mindmap_id=mindmap_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mindmap introuvable"
        )
    return None
