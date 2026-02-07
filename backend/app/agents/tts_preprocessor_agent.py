"""
Agent TTSPreprocessor: transforme un texte pour qu'il soit lu de façon fluide par une synthèse vocale (TTS).

- Supprime ou adapte la syntaxe Markdown (titres, gras, listes, liens) pour ne pas la prononcer.
- Reformule si besoin pour une écoute naturelle (abrégés, chiffres, etc.).
- Conserve le sens et la structure du contenu.
"""

import logging

from agno.agent import Agent

from app.agents.base import AgentBase, AgentResponse
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TTSPreprocessorAgent(AgentBase):
    """Agent qui prépare un texte pour une lecture TTS fluide (sans prononcer le markdown)."""

    @property
    def name(self) -> str:
        return "TTSPreprocessor"

    @property
    def description(self) -> str:
        return "Transforme un texte pour une synthèse vocale fluide (sans markdown ni symboles prononcés)"

    def _create_agent(self) -> Agent:
        """Crée l'agent Agno pour le prétraitement TTS."""
        return Agent(
            name=self.name,
            model=self.model,
            instructions="""Tu es un assistant qui transforme du texte pour qu'il soit lu à voix haute de façon fluide par une synthèse vocale (TTS).

RÈGLES:
1. Ne fais JAMAIS prononcer la syntaxe Markdown: pas de "dièse", "astérisque", "tiret", "crochet", "parenthèse" pour les liens, etc.
2. Titres (# ## ###): remplace par une phrase naturelle ou supprime le symbole, garde le contenu.
3. Gras/italique (**texte**, *texte*): garde uniquement le texte, sans prononcer "étoiles".
4. Listes à puces (- ou *): garde le contenu, tu peux introduire par "Premier point:", "Ensuite:", etc. si ça améliore l'écoute.
5. Liens [texte](url): garde uniquement "texte" (ou "lien vers ..." si le texte est une URL).
6. Chiffres et abréviations: écris en toutes lettres si ça améliore la prononciation (ex: "5" peut rester "cinq", "km" → "kilomètres").
7. Conserve le sens et l'ordre du contenu. Sois concis: n'ajoute pas de commentaires, uniquement le texte prêt à être lu.
8. Langue: conserve la langue du texte (souvent français).

Réponds UNIQUEMENT avec le texte transformé, sans préambule ni guillemets. Aucune autre phrase avant ou après.""",
        )

    async def execute(self, input_text: str, **kwargs) -> AgentResponse:
        """
        Transforme le texte pour le TTS.

        Args:
            input_text: Texte brut (éventuellement en Markdown) à adapter pour la lecture vocale.

        Returns:
            AgentResponse avec data={"text": "texte prêt pour TTS"} ou erreur.
        """
        if not input_text or not input_text.strip():
            return AgentResponse(
                success=True,
                message="Texte vide",
                data={"text": ""},
            )

        try:
            settings = get_settings()
            if getattr(settings, "skip_agent_llm", False):
                logger.info("[TTSPreprocessor] SKIP_AGENT_LLM activé, retour du texte tel quel")
                return AgentResponse(
                    success=True,
                    message="Prétraitement ignoré (SKIP_AGENT_LLM)",
                    data={"text": input_text.strip()},
                )

            # Détecter si c'est un texte météo (températures, précipitations, jours de la semaine, etc.)
            text_lower = input_text.lower()
            is_weather = any(
                keyword in text_lower
                for keyword in [
                    "météo",
                    "température",
                    "précipitation",
                    "aujourd'hui",
                    "demain",
                    "lundi",
                    "mardi",
                    "mercredi",
                    "jeudi",
                    "vendredi",
                    "samedi",
                    "dimanche",
                    "°c",
                    "mm de précipitations",
                    "averses",
                    "pluie",
                    "ensoleillé",
                    "nuageux",
                ]
            )

            if is_weather:
                prompt = """Transforme ce texte météo pour qu'il soit lu à voix haute de façon naturelle, comme si tu racontais la météo à un ami.

STYLE CONVERSATIONNEL:
- Commence par "Bonjour" ou "Voici la météo" si c'est le début
- Utilise un ton naturel et chaleureux, comme si tu parlais à quelqu'un
- Remplace les listes structurées par des phrases fluides (ex: "Aujourd'hui il fera 10 degrés maximum, 6 degrés minimum, avec des averses de pluie légères")
- Pour les jours suivants, utilise "Demain", "Lundi", "Mardi", etc. de façon naturelle
- Évite les répétitions de "température max", "température min" - dis plutôt "il fera entre X et Y degrés"
- Si précipitations: "il y aura X millimètres de pluie" ou "pas de pluie prévue"
- Sois concis mais naturel, comme une conversation

RÈGLES:
- Ne prononce JAMAIS le markdown (**, #, -, etc.)
- Transforme les données brutes en phrases fluides
- Garde toutes les informations importantes (températures, temps, précipitations, dates)

Texte météo à transformer:
""" + input_text.strip()
            else:
                prompt = f"Transforme ce texte pour qu'il soit lu à voix haute (TTS). Ne prononce pas le markdown.\n\nTexte à transformer:\n{input_text.strip()}"
            
            response = await self.agent.arun(prompt)
            content = getattr(response, "content", None) or str(response)
            cleaned = (content or "").strip()
            if not cleaned:
                cleaned = input_text.strip()

            logger.info("[TTSPreprocessor] Texte transformé: %d → %d caractères", len(input_text), len(cleaned))
            return AgentResponse(
                success=True,
                message="Texte prêt pour TTS",
                data={"text": cleaned},
            )
        except Exception as e:
            logger.warning("[TTSPreprocessor] Erreur, utilisation du texte brut: %s", e)
            return AgentResponse(
                success=True,
                message="Fallback texte brut",
                data={"text": input_text.strip()},
            )


# Instance singleton
tts_preprocessor_agent = TTSPreprocessorAgent()
