"""
Route météo : retour formaté directement depuis l'API Open-Meteo (sans agent IA).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_active_user
from app.models.user import User
from app.tools.weather_tools import get_weather_formatted

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("")
def get_weather(
    location: str = Query(..., description="Ville ou lieu (ex: Paris, Lyon)"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Météo du jour et de la semaine à venir pour une localisation.
    Formatage direct depuis l'API Open-Meteo, sans agent IA.
    """
    formatted_text, raw_data = get_weather_formatted(location)
    if raw_data is None:
        return {"location": location, "formatted": formatted_text, "daily": None, "error": True}
    return {
        "location": raw_data["lieu"],
        "formatted": formatted_text,
        "daily": raw_data.get("daily"),
        "error": False,
    }
