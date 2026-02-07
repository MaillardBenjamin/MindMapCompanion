"""
Service de synthèse vocale (TTS) pour générer de l'audio à partir de texte.
Utilise gTTS (Google Text-to-Speech).
"""
import logging
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)

# Limite de caractères pour éviter des requêtes TTS trop longues (timeout / quota)
TTS_MAX_CHARS = 5000


def text_to_speech_mp3(
    text: str,
    lang: str = "fr",
    slow: bool = False,
) -> Optional[bytes]:
    """
    Génère un fichier MP3 à partir du texte (TTS).

    Args:
        text: Texte à synthétiser.
        lang: Code langue IETF (défaut: "fr").
        slow: Parole plus lente si True.

    Returns:
        Octets du fichier MP3, ou None en cas d'erreur.
    """
    if not text or not text.strip():
        logger.warning("[TTS] Texte vide, pas de génération")
        return None

    # Tronquer pour éviter timeouts
    if len(text) > TTS_MAX_CHARS:
        text = text[:TTS_MAX_CHARS] + "..."
        logger.info("[TTS] Texte tronqué à %d caractères", TTS_MAX_CHARS)

    try:
        from gtts import gTTS

        tts = gTTS(text=text, lang=lang, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        mp3_bytes = fp.getvalue()
        logger.info("[TTS] Audio généré: %d octets", len(mp3_bytes))
        return mp3_bytes
    except Exception as e:
        logger.exception("[TTS] Erreur lors de la génération: %s", e)
        return None
