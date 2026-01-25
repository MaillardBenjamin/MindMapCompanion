from fastapi import APIRouter, Depends
from app.schemas.user import UserResponse
from app.api.deps import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Récupère les informations de l'utilisateur actuellement connecté"""
    return current_user
