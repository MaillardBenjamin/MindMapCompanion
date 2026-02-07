from pydantic import BaseModel
from typing import Optional


class TriggerManualExecuteRequest(BaseModel):
    """Requête pour lancer un trigger manuellement"""
    trigger_id: Optional[str] = None  # Optionnel si on veut créer une action temporaire
    task_type: str  # "agent" ou "action"
    task_id: str  # ID de l'agent configurable ou de l'action
    output_type: str  # "screen", "email", "audio_tts", "audio_email"
    input_text: Optional[str] = None  # Texte d'entrée pour l'agent (si task_type = "agent")
    agent_options: Optional[dict] = None  # Paramètres dynamiques de l'agent (input_schema)
    email_config: Optional[dict] = None  # Configuration email si output_type = "email"


class TriggerManualExecuteResponse(BaseModel):
    """Réponse du lancement manuel d'un trigger"""
    success: bool
    message: str
    execution_id: Optional[str] = None
    output: Optional[dict] = None
    email_sent: Optional[bool] = None
