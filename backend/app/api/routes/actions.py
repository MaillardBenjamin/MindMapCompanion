from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.mindmap import (
    ActionCreate,
    ActionUpdate,
    ActionResponse,
)
from app.crud import mindmap as crud_mindmap

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.post("", response_model=ActionResponse, status_code=status.HTTP_201_CREATED)
def create_action(
    action: ActionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crée une nouvelle action sur un trigger
    
    Types d'actions supportés:
    - api_call: Appel API externe
    - notification: Notification système
    - task: Création de tâche
    - script: Exécution de script
    - email: Envoi d'email (config: {"to": "email@example.com", "subject": "...", "body": "..."})
    """
    db_action = crud_mindmap.create_action(db, action=action, user_id=current_user.id)
    if not db_action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger introuvable ou vous n'avez pas accès à ce trigger"
        )
    return db_action


@router.get("/trigger/{trigger_id}", response_model=List[ActionResponse])
def get_actions_by_trigger(
    trigger_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupère toutes les actions d'un trigger"""
    actions = crud_mindmap.get_actions_by_trigger(db, trigger_id=trigger_id, user_id=current_user.id)
    return actions


@router.get("/{action_id}", response_model=ActionResponse)
def get_action(
    action_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupère une action"""
    db_action = crud_mindmap.get_action(db, action_id=action_id, user_id=current_user.id)
    if not db_action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action introuvable"
        )
    return db_action


@router.put("/{action_id}", response_model=ActionResponse)
def update_action(
    action_id: int,
    action_update: ActionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Met à jour une action"""
    db_action = crud_mindmap.update_action(
        db, action_id=action_id, user_id=current_user.id, action_update=action_update
    )
    if not db_action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action introuvable"
        )
    return db_action


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action(
    action_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Supprime une action"""
    success = crud_mindmap.delete_action(db, action_id=action_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action introuvable"
        )
    return None
