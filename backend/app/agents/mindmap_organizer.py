"""
Agent MindmapOrganizer: Organise le texte saisi dans le mindmap.

Cet agent analyse le texte entré par l'utilisateur et:
1. Identifie les thèmes principaux et sous-thèmes
2. Décide si créer un nouveau nœud ou compléter un existant
3. Génère un titre et une description appropriés
4. Positionne logiquement le contenu dans la hiérarchie du mindmap
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from agno.agent import Agent

from sqlalchemy.orm import Session

from app.agents.base import AgentBase, AgentResponse
from app.crud.mindmap import (
    get_nodes_by_mindmap,
    create_node,
    update_node,
    get_node,
)
from app.schemas.mindmap import NodeCreate, NodeUpdate

# Logger pour le débogage
logger = logging.getLogger(__name__)


class NodeSuggestion(BaseModel):
    """Suggestion de nœud à créer ou mettre à jour"""
    action: str  # "create" ou "update"
    node_id: Optional[int] = None  # Pour update
    parent_id: Optional[int] = None  # Pour create
    label: str
    description: str
    reasoning: str  # Explication du choix


class OrganizeResult(BaseModel):
    """Résultat de l'organisation"""
    suggestions: List[NodeSuggestion]
    summary: str


class MindmapOrganizerAgent(AgentBase):
    """Agent qui organise le texte dans le mindmap"""
    
    @property
    def name(self) -> str:
        return "MindmapOrganizer"
    
    @property
    def description(self) -> str:
        return "Organise le texte saisi dans le mindmap en identifiant les thèmes et sous-thèmes"
    
    def _create_agent(self) -> Agent:
        """Crée l'agent Agno pour l'organisation du mindmap"""
        return Agent(
            name=self.name,
            model=self.model,
            instructions="""Tu es un assistant expert en organisation de l'information et en création de mindmaps.

Ton rôle est d'analyser le texte fourni par l'utilisateur et de déterminer comment l'organiser 
dans un mindmap existant de manière logique et hiérarchique.

Pour chaque texte reçu, tu dois:

1. ANALYSER le contenu pour identifier:
   - Les thèmes principaux
   - Les sous-thèmes et détails
   - Les relations logiques entre les idées
   - TOUS les éléments à créer (parent ET enfants)

2. COMPARER avec les nœuds existants du mindmap pour décider:
   - Si le contenu correspond à un nœud existant → UPDATE (enrichir SEULEMENT label et description, JAMAIS le parent_id)
   - Si c'est un nouveau thème → CREATE un nouveau nœud au bon endroit
   - Si le texte mentionne plusieurs niveaux hiérarchiques, crée TOUS les niveaux nécessaires
   - ⚠️ IMPORTANT: L'action "update" NE PEUT PAS modifier le parent_id. Pour changer le parent, utilise "create" + "move" ou crée un nouveau nœud

3. Pour chaque suggestion, fournir:
   - Un TITRE concis et explicite (max 30 caractères)
   - Une DESCRIPTION claire et informative
   - Le PARENT approprié (ou null pour un nœud racine)

RÈGLES CRITIQUES:
- Si le texte mentionne "ajouter X à Y" ou "X dans Y", crée DEUX suggestions:
  1. Si Y n'existe pas : créer Y UNE SEULE FOIS (sans parent ou avec le parent approprié)
  2. Toujours créer X comme enfant de Y (même si Y vient d'être créé dans la même réponse, utilise son ID)

- ⚠️ NE CRÉE JAMAIS DEUX NŒUDS AVEC LE MÊME LABEL dans la même réponse. Si tu dois créer un parent et des enfants, crée UN SEUL parent et utilise son ID pour tous les enfants.

- Si le texte mentionne plusieurs items à ajouter (ex: "ajouter pain, lait et œufs à la liste de courses"), crée UNE suggestion pour chaque item, toutes avec le même parent_id

- Si le texte fait référence à un nœud existant, utilise son ID EXACT comme parent_id

- Sois EXHAUSTIF : si le texte mentionne plusieurs éléments hiérarchiques, crée TOUS les nœuds nécessaires, pas seulement le parent

- Si le texte contient plusieurs idées distinctes, crée plusieurs suggestions

- Préfère mettre à jour un nœud existant plutôt que d'en créer un similaire

- Garde les titres courts et percutants (max 30 caractères)

- Si tu crées un parent et des enfants dans la même réponse:
  * Crée D'ABORD le parent (première suggestion)
  * Crée ENSUITE les enfants en utilisant l'ID du parent créé (pas un ID existant aléatoire)
  * Exemple: Si tu crées "Recherche d'emploi" comme parent, et "Lady - RH" comme enfant, utilise l'ID du nœud "Recherche d'emploi" que tu viens de créer, PAS un autre ID

RÉPONDS UNIQUEMENT EN JSON valide, sans texte avant ou après. Format exact requis:
{
    "suggestions": [
        {
            "action": "create" ou "update",
            "node_id": null (pour create) ou ID du nœud à mettre à jour (pour update),
            "parent_id": null ou ID du parent (UNIQUEMENT pour "create", IGNORÉ pour "update"),
            "label": "Titre du nœud",
            "description": "Description détaillée",
            "reasoning": "Explication de ton choix"
        }
    ],
    "summary": "Résumé des actions proposées"
}

RÈGLES POUR LES ACTIONS:
- "create": parent_id OBLIGATOIRE si ce n'est pas une racine (ID ou null)
- "update": parent_id est IGNORÉ - ne peut modifier QUE label et description, JAMAIS le parent

IMPORTANT CRITIQUE:
- Réponds UNIQUEMENT avec du JSON valide, rien d'autre
- AUCUN commentaire dans le JSON (pas de // ou /* */)
- parent_id doit être un nombre (ID) ou null, PAS un commentaire ou du texte
- Si tu crées plusieurs nœuds hiérarchiques et que le parent vient d'être créé, utilise son ID numérique réel
""",
            output_schema=OrganizeResult,
            parse_response=True,
            use_json_mode=True,
            structured_outputs=True,
        )
    
    def _format_existing_nodes(self, nodes: List[Any]) -> str:
        """Formate les nœuds existants pour le contexte de l'agent avec la hiérarchie"""
        if not nodes:
            return "Aucun nœud existant. Le mindmap est vide."
        
        # Construire un dictionnaire pour accès rapide
        nodes_dict = {n.id: n for n in nodes}
        
        # Trouver les nœuds racines
        root_nodes = [n for n in nodes if n.is_root or n.parent_id is None]
        
        # Ensemble pour suivre les nœuds visités et détecter les cycles
        visited_nodes = set()
        
        def build_tree_representation(node, depth=0, visited_path=None) -> str:
            """Construit une représentation arborescente d'un nœud et de ses enfants"""
            # Protection contre la récursion infinie (cycles)
            if visited_path is None:
                visited_path = set()
            
            # Vérifier si ce nœud est déjà dans le chemin (cycle détecté)
            if node.id in visited_path:
                indent = "  " * depth
                return f"{indent}└── [ID {node.id}] '{node.label}' ⚠️ [CYCLE DÉTECTÉ - nœud déjà visité]"
            
            # Limiter la profondeur pour éviter une récursion trop profonde
            if depth > 50:
                indent = "  " * depth
                return f"{indent}└── [ID {node.id}] '{node.label}' ⚠️ [Profondeur maximale atteinte]"
            
            # Ajouter ce nœud au chemin visité
            new_visited_path = visited_path.copy()
            new_visited_path.add(node.id)
            visited_nodes.add(node.id)
            
            indent = "  " * depth
            prefix = "└── " if depth > 0 else ""
            
            result = f"{indent}{prefix}[ID {node.id}] '{node.label}'"
            if node.description:
                desc_preview = (node.description[:50] + "..." if len(node.description) > 50 else node.description)
                result += f"\n{indent}    └─ {desc_preview}"
            
            # Ajouter les enfants
            children = [n for n in nodes if n.parent_id == node.id]
            for child in children:
                result += "\n" + build_tree_representation(child, depth + 1, new_visited_path)
            
            return result
        
        tree_repr = "Structure actuelle du mindmap (hiérarchie):\n\n"
        for root in root_nodes:
            tree_repr += build_tree_representation(root) + "\n\n"
        
        # Afficher les nœuds qui n'ont pas été visités (probablement orphelins ou cycles)
        unvisited = [n for n in nodes if n.id not in visited_nodes]
        if unvisited:
            tree_repr += "\n⚠️ Nœuds non visités (possiblement orphelins ou cycles):\n"
            for node in unvisited:
                tree_repr += f"  [ID {node.id}] '{node.label}' (parent_id={node.parent_id})\n"
        
        # Ajouter aussi un résumé par ID pour référence rapide
        tree_repr += "\nRéférence rapide (ID → Label):\n"
        for node in nodes:
            tree_repr += f"  ID {node.id}: '{node.label}' (parent: {node.parent_id or 'racine'})\n"
        
        return tree_repr

    @staticmethod
    def _clean_json_text(text: str) -> str:
        """Nettoie un texte supposé JSON (retire commentaires, code fences, virgules traînantes)."""
        cleaned = (text or "").strip()

        # Extraire le contenu d'un éventuel bloc ```json ... ```
        fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        # Supprimer les commentaires JavaScript
        cleaned = re.sub(r"//.*?$", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

        # Nettoyer les virgules avant } ou ]
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
        return cleaned.strip()

    @staticmethod
    def _extract_first_json_object(text: str) -> Optional[str]:
        """
        Extrait le premier objet JSON équilibré trouvé dans un texte.
        Gère les accolades présentes dans du texte explicatif autour.
        """
        if not text:
            return None

        start = text.find("{")
        if start < 0:
            return None

        depth = 0
        in_string = False
        escape = False
        for i, ch in enumerate(text[start:], start=start):
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == "\"":
                    in_string = False
                continue

            if ch == "\"":
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    @staticmethod
    def _parse_markdown_suggestions(text: str) -> Optional[OrganizeResult]:
        """
        Fallback: parse une réponse non-JSON structurée en sections Markdown.
        Exemple supporté:
        - Action: create
        - Label: "..."
        - Parent_id: 1
        """
        if not text:
            return None

        # Découpe par sections numérotées "1. **...**"
        blocks = re.findall(
            r"(?ms)(?:^|\n)\s*\d+\.\s+\*\*.*?\*\*.*?(?=(?:\n\s*\d+\.\s+\*\*|\Z))",
            text,
        )
        if not blocks:
            blocks = [text]

        suggestions: List[NodeSuggestion] = []
        for block in blocks:
            plain = re.sub(r"[`*]", "", block)

            action_match = re.search(r"\bAction\b\s*[:：]\s*(create|update)\b", plain, re.IGNORECASE)
            label_line_match = re.search(r"\bLabel\b\s*[:：]\s*(.+)", plain, re.IGNORECASE)
            parent_match = re.search(r"\bParent[_ ]?id\b\s*[:：]\s*(null|\d+)", plain, re.IGNORECASE)
            node_match = re.search(r"\bNode[_ ]?id\b\s*[:：]\s*(null|\d+)", plain, re.IGNORECASE)
            reason_match = re.search(r"\bRaison\b\s*[:：]\s*(.+)", plain, re.IGNORECASE)

            if not action_match or not label_line_match:
                continue

            action = action_match.group(1).lower().strip()
            label_line = label_line_match.group(1).strip().splitlines()[0].strip()
            # Si la valeur est entre guillemets doubles, conserver le contenu entre guillemets
            quoted_double = re.search(r'"([^"]+)"', label_line)
            if quoted_double:
                label = quoted_double.group(1).strip()
            else:
                # Nettoyage simple: retirer les parenthèses explicatives de fin
                label = re.sub(r"\s*\([^)]*\)\s*$", "", label_line).strip(" -")

            if not label:
                continue

            parent_id: Optional[int] = None
            if parent_match:
                raw_parent = parent_match.group(1).strip().lower()
                if raw_parent != "null":
                    try:
                        parent_id = int(raw_parent)
                    except ValueError:
                        parent_id = None

            node_id: Optional[int] = None
            if node_match:
                raw_node = node_match.group(1).strip().lower()
                if raw_node != "null":
                    try:
                        node_id = int(raw_node)
                    except ValueError:
                        node_id = None

            reasoning = reason_match.group(1).strip() if reason_match else "Suggestion extraite en mode fallback."
            description = label

            suggestions.append(
                NodeSuggestion(
                    action=action,
                    node_id=node_id if action == "update" else None,
                    parent_id=parent_id if action == "create" else None,
                    label=label,
                    description=description,
                    reasoning=reasoning,
                )
            )

        if not suggestions:
            return None

        return OrganizeResult(
            suggestions=suggestions,
            summary="Suggestions extraites depuis une réponse non-JSON (mode fallback).",
        )

    def _parse_agent_response(self, content: Any) -> OrganizeResult:
        """Parse la réponse de l'agent avec fallback robuste (JSON strict -> extraction -> markdown)."""
        if isinstance(content, OrganizeResult):
            return content

        if isinstance(content, dict):
            return OrganizeResult(**content)

        text = str(content or "").strip()
        if not text:
            raise ValueError("Réponse vide de l'agent.")

        # 1) Essai direct sur contenu nettoyé
        cleaned = self._clean_json_text(text)
        try:
            parsed = json.loads(cleaned)
            return OrganizeResult(**parsed)
        except Exception:
            pass

        # 2) Essai sur premier objet JSON trouvé dans le texte
        extracted = self._extract_first_json_object(text)
        if extracted:
            try:
                parsed = json.loads(self._clean_json_text(extracted))
                return OrganizeResult(**parsed)
            except Exception:
                pass

        # 3) Fallback Markdown/suggestions textuelles
        fallback = self._parse_markdown_suggestions(text)
        if fallback:
            logger.warning("[MindmapOrganizer] Réponse non-JSON parsée en mode fallback.")
            return fallback

        raise ValueError("Réponse non parsable (ni JSON valide, ni suggestions exploitables).")
    
    async def execute(
        self,
        db: Session,
        mindmap_id: int,
        user_id: int,
        text: str,
        auto_apply: bool = True,
    ) -> AgentResponse:
        """
        Exécute l'agent pour organiser le texte dans le mindmap.
        
        Args:
            db: Session de base de données
            mindmap_id: ID du mindmap cible
            user_id: ID de l'utilisateur
            text: Texte à organiser
            auto_apply: Si True, applique automatiquement les suggestions
        
        Returns:
            AgentResponse avec les suggestions et les nœuds créés/modifiés
        """
        try:
            logger.info(f"[MindmapOrganizer] Début d'exécution - mindmap_id={mindmap_id}, text='{text[:100]}...'")
            
            # Récupérer les nœuds existants
            existing_nodes = get_nodes_by_mindmap(db, mindmap_id, user_id)
            logger.info(f"[MindmapOrganizer] {len(existing_nodes)} nœuds existants trouvés")
            
            context = self._format_existing_nodes(existing_nodes)
            logger.debug(f"[MindmapOrganizer] Contexte formaté:\n{context[:500]}...")
            
            # Construire le prompt
            prompt = f"""
{context}

TEXTE À ORGANISER:
{text}

Analyse ce texte et propose comment l'organiser dans le mindmap.

INSTRUCTIONS CRITIQUES:
- Si le texte dit "ajouter X à Y" ou "X dans Y":
  1. Si Y n'existe pas, crée Y d'abord (avec son propre parent_id approprié)
  2. CRÉE TOUJOURS X comme enfant de Y (même si Y vient d'être créé, utilise son ID dans parent_id)

- Si le texte mentionne une ACTION pour un THÈME (ex: "mail à la maîtresse pour la sortie scolaire"):
  1. Crée d'abord le THÈME parent (ex: "Sortie scolaire")
  2. Crée ensuite l'ACTION comme enfant du thème (ex: "Mail à la maîtresse" avec parent_id = ID du thème "Sortie scolaire")
  
  IMPORTANT: Si le texte contient une préposition comme "pour", "concernant", "relatif à", cela indique souvent une hiérarchie:
  - "mail à la maîtresse pour la sortie" → Thème="Sortie scolaire" (parent), Action="Mail à la maîtresse" (enfant)

- Si le texte mentionne plusieurs items (ex: "ajouter pain, lait à la liste"), crée UNE suggestion par item, toutes avec le même parent_id

- Si le texte fait référence à un nœud existant, trouve son ID exact dans la structure et utilise-le comme parent_id

- Ne crée PAS seulement le parent si le texte mentionne aussi des enfants - crée TOUS les niveaux hiérarchiques nécessaires

- IDENTIFIE TOUJOURS les thèmes, sujets ou contextes dans le texte - ils doivent être des nœuds parents, pas seulement des descriptions

- Exemple 1: "ajouter du pain à la liste de courses"
  → Si "liste de courses" n'existe pas: 2 suggestions
     1. action="create", label="Liste de courses", parent_id=<parent approprié>
     2. action="create", label="Pain", parent_id=<ID du nœud "Liste de courses" créé ci-dessus>
  → Si "liste de courses" existe (ID=5): 1 suggestion
     1. action="create", label="Pain", parent_id=5

- Exemple 2: "mail à la maîtresse pour la sortie scolaire"
  → 2 suggestions REQUISES:
     1. action="create", label="Sortie scolaire", parent_id=<parent approprié>
     2. action="create", label="Mail à la maîtresse", parent_id=<ID du nœud "Sortie scolaire" créé ci-dessus>

- Vérifie attentivement les labels des nœuds existants pour faire correspondre les références du texte
- Utilise l'arbre hiérarchique fourni pour comprendre les relations parent-enfant
"""
            
            logger.info(f"[MindmapOrganizer] Envoi du prompt à l'agent IA (longueur: {len(prompt)} caractères)")
            
            # Exécuter l'agent
            response = self.agent.run(prompt)
            raw_content = getattr(response, "content", response)
            raw_as_text = raw_content if isinstance(raw_content, str) else json.dumps(
                raw_content if isinstance(raw_content, dict) else str(raw_content),
                ensure_ascii=False,
            )

            logger.info(f"[MindmapOrganizer] Réponse reçue de l'agent (longueur: {len(raw_as_text)} caractères)")
            logger.info(f"[MindmapOrganizer] ========== SORTIE COMPLÈTE DU MODÈLE IA ==========")
            logger.info(f"[MindmapOrganizer] {raw_as_text}")
            logger.info(f"[MindmapOrganizer] =================================================")

            # Parser la réponse (JSON strict puis fallback)
            try:
                result = self._parse_agent_response(raw_content)
                logger.info(
                    f"[MindmapOrganizer] Réponse parsée avec succès: {len(result.suggestions)} suggestions"
                )
                
                # Logger chaque suggestion
                for idx, suggestion in enumerate(result.suggestions):
                    logger.info(f"[MindmapOrganizer] Suggestion {idx+1}: action={suggestion.action}, "
                              f"node_id={suggestion.node_id}, parent_id={suggestion.parent_id}, "
                              f"label='{suggestion.label}'")
                    
            except ValueError as e:
                logger.error(f"[MindmapOrganizer] Erreur lors du parsing de la réponse: {e}")
                logger.error(f"[MindmapOrganizer] Contenu reçu: {raw_as_text[:500]}")
                return AgentResponse(
                    success=False,
                    message="Erreur lors du parsing de la réponse de l'agent",
                    error=str(e),
                )
            
            created_nodes = []
            updated_nodes = []
            
            # Créer un map des labels créés -> ID réel pour corriger les références futures
            label_to_id_map: Dict[str, int] = {}
            
            # Détecter et corriger les doublons dans les suggestions (même label créé plusieurs fois)
            # Si plusieurs suggestions créent le même label, on garde seulement la première et on marque les autres pour suppression
            seen_labels: Dict[str, int] = {}  # label -> index de la première suggestion
            suggestions_to_remove = set()
            
            for idx, suggestion in enumerate(result.suggestions):
                if suggestion.action == "create" and suggestion.label:
                    label_lower = suggestion.label.lower().strip()
                    if label_lower in seen_labels:
                        # Doublon détecté - marquer pour suppression
                        first_idx = seen_labels[label_lower]
                        suggestions_to_remove.add(idx)
                        logger.warning(f"[MindmapOrganizer] ⚠️ Doublon détecté: suggestion {idx+1} crée le même label "
                                     f"'{suggestion.label}' que la suggestion {first_idx+1}. "
                                     f"La suggestion {idx+1} sera ignorée et les enfants utiliseront le nœud de la suggestion {first_idx+1}.")
                    else:
                        seen_labels[label_lower] = idx
            
            # Filtrer les suggestions en double
            if suggestions_to_remove:
                original_count = len(result.suggestions)
                result.suggestions = [s for idx, s in enumerate(result.suggestions) if idx not in suggestions_to_remove]
                logger.info(f"[MindmapOrganizer] {len(suggestions_to_remove)} suggestion(s) en double supprimée(s). "
                          f"Passage de {original_count} à {len(result.suggestions)} suggestions.")
            
            if auto_apply:
                logger.info(f"[MindmapOrganizer] Application automatique de {len(result.suggestions)} suggestions")
                
                # Appliquer les suggestions
                for idx, suggestion in enumerate(result.suggestions):
                    logger.info(f"[MindmapOrganizer] Traitement suggestion {idx+1}/{len(result.suggestions)}: "
                              f"action={suggestion.action}, label='{suggestion.label}'")
                    
                    if suggestion.action == "create":
                        logger.info(f"[MindmapOrganizer] Création d'un nouveau nœud: '{suggestion.label}' "
                                  f"(parent_id={suggestion.parent_id})")
                        
                        # Créer un nouveau nœud
                        # Déterminer la position en fonction du parent
                        position_x = 400
                        position_y = 100
                        
                        if suggestion.parent_id:
                            logger.info(f"[MindmapOrganizer] Recherche du parent avec ID={suggestion.parent_id}")
                            parent_node = get_node(db, suggestion.parent_id, user_id)
                            
                            # Toujours vérifier si cette suggestion devrait être liée à un nœud créé précédemment
                            # même si le parent_id pointe vers un nœud existant (car l'IA peut se tromper)
                            found_parent = None
                            context_text = ((suggestion.reasoning or "") + " " + (suggestion.description or "")).lower()
                            
                            # Vérifier si le parent fourni par l'IA est cohérent avec le contexte
                            parent_seems_incorrect = False
                            if parent_node:
                                parent_label_lower = parent_node.label.lower()
                                parent_desc_lower = (getattr(parent_node, 'description', None) or "").lower()
                                parent_context = (parent_label_lower + " " + parent_desc_lower).lower()
                                
                                # Extraire les mots significatifs du contexte de la suggestion et du parent
                                context_words = set(w for w in context_text.split() if len(w) > 3)
                                parent_words = set(w for w in parent_context.split() if len(w) > 3)
                                common_with_parent = context_words.intersection(parent_words)
                                
                                # Si très peu de mots en commun avec le parent fourni, il est probablement incorrect
                                if len(common_with_parent) < 1:
                                    parent_seems_incorrect = True
                                    logger.info(f"[MindmapOrganizer] Parent ID={suggestion.parent_id} ('{parent_node.label}') "
                                              f"semble incohérent avec le contexte de '{suggestion.label}' "
                                              f"(peu de mots communs: {common_with_parent})")
                            
                            # Chercher dans les suggestions précédentes pour détecter des références sémantiques
                            for prev_suggestion in result.suggestions[:idx]:
                                if prev_suggestion.action == "create" and prev_suggestion.label:
                                    prev_label_lower = prev_suggestion.label.lower()
                                    prev_desc_lower = (prev_suggestion.description or "").lower()
                                    
                                    # Vérifier si le contexte mentionne explicitement le label du parent précédent
                                    # ou des mots-clés du label (pour gérer les variations)
                                    label_words = set(w for w in prev_label_lower.split() if len(w) > 3)
                                    context_words = set(w for w in context_text.split() if len(w) > 3)
                                    label_in_context = prev_label_lower in context_text or len(label_words.intersection(context_words)) >= 1
                                    
                                    if (label_in_context or 
                                        "qui vient d'être créé" in context_text or
                                        "créé précédemment" in context_text or
                                        "créé ci-dessus" in context_text):
                                        # Chercher le nœud créé correspondant (prendre le plus récent si plusieurs)
                                        for created in reversed(created_nodes):  # Parcourir de la fin pour prendre le plus récent
                                            if created.get("label") == prev_suggestion.label:
                                                found_parent = created
                                                logger.info(f"[MindmapOrganizer] Correspondance trouvée via label: "
                                                          f"'{suggestion.label}' -> '{prev_suggestion.label}' (ID={found_parent['id']})")
                                                break
                                        if found_parent:
                                            break
                                    
                                    # Vérifier aussi la correspondance sémantique via les descriptions
                                    if not found_parent and prev_desc_lower and suggestion.description:
                                        desc_lower = suggestion.description.lower()
                                        # Extraire les mots significatifs (plus de 3 caractères)
                                        prev_words = set(w for w in prev_desc_lower.split() if len(w) > 3)
                                        desc_words = set(w for w in desc_lower.split() if len(w) > 3)
                                        common_words = prev_words.intersection(desc_words)
                                        # Si au moins 2 mots significatifs en commun, c'est probablement lié
                                        if len(common_words) >= 2:
                                            for created in reversed(created_nodes):  # Parcourir de la fin pour prendre le plus récent
                                                if created.get("label") == prev_suggestion.label:
                                                    found_parent = created
                                                    logger.info(f"[MindmapOrganizer] Correspondance trouvée via description: "
                                                              f"'{suggestion.label}' -> '{prev_suggestion.label}' (ID={found_parent['id']}, "
                                                              f"mots communs: {common_words})")
                                                    break
                                            if found_parent:
                                                break
                                    
                                    # Vérifier aussi si le label de la suggestion actuelle contient des mots
                                    # du label ou de la description du parent précédent
                                    if not found_parent:
                                        current_label_words = set(w for w in suggestion.label.lower().split() if len(w) > 3)
                                        # Si le label actuel partage des mots avec le label ou la description du parent précédent
                                        if (len(current_label_words.intersection(label_words)) >= 1 or
                                            (prev_desc_lower and len(current_label_words.intersection(set(w for w in prev_desc_lower.split() if len(w) > 3))) >= 1)):
                                            # Mais seulement si la description actuelle mentionne aussi des concepts du parent
                                            if suggestion.description:
                                                desc_lower = suggestion.description.lower()
                                                desc_words = set(w for w in desc_lower.split() if len(w) > 3)
                                                if len(desc_words.intersection(label_words)) >= 1 or (prev_desc_lower and len(desc_words.intersection(set(w for w in prev_desc_lower.split() if len(w) > 3))) >= 1):
                                                    for created in reversed(created_nodes):  # Parcourir de la fin pour prendre le plus récent
                                                        if created.get("label") == prev_suggestion.label:
                                                            found_parent = created
                                                            logger.info(f"[MindmapOrganizer] Correspondance trouvée via analyse sémantique: "
                                                                      f"'{suggestion.label}' -> '{prev_suggestion.label}' (ID={found_parent['id']})")
                                                            break
                                                    if found_parent:
                                                        break
                            
                            # Si le parent n'existe pas dans la DB, chercher aussi par index
                            if not parent_node:
                                # Vérifier si le parent_id correspond à un index (1-based) dans les suggestions précédentes
                                if 1 <= suggestion.parent_id <= len(result.suggestions):
                                    prev_idx = suggestion.parent_id - 1
                                    if prev_idx < idx:  # Le parent doit être créé avant (idx est 0-based)
                                        prev_suggestion = result.suggestions[prev_idx]
                                        if prev_suggestion.action == "create" and prev_suggestion.label:
                                            # Chercher dans les nœuds créés avec ce label (prendre le plus récent)
                                            for created in reversed(created_nodes):  # Parcourir de la fin pour prendre le plus récent
                                                if created.get("label") == prev_suggestion.label:
                                                    found_parent = created
                                                    break
                            
                            # Si on a trouvé un parent dans les nœuds créés précédemment, l'utiliser
                            # (surtout si le parent fourni par l'IA semble incorrect)
                            if found_parent:
                                logger.info(f"[MindmapOrganizer] Parent corrigé: ID={suggestion.parent_id} -> ID={found_parent['id']} "
                                          f"(référence au nœud '{found_parent['label']}' créé précédemment)")
                                suggestion.parent_id = found_parent["id"]
                                parent_node = get_node(db, found_parent["id"], user_id)
                            elif parent_node and parent_seems_incorrect and found_parent is None:
                                # Si le parent existe mais semble incorrect et qu'on n'a pas trouvé de correspondance,
                                # on log un avertissement mais on garde le parent original pour éviter les faux positifs
                                logger.warning(f"[MindmapOrganizer] ⚠️ Parent ID={suggestion.parent_id} ('{parent_node.label}') "
                                             f"semble incohérent pour '{suggestion.label}' mais aucune correspondance trouvée "
                                             f"dans les nœuds créés précédemment")
                            
                            # Mettre à jour le label_to_id_map pour les futures références
                            if parent_node:
                                label_to_id_map[parent_node.label.lower()] = parent_node.id
                            
                            if parent_node:
                                logger.info(f"[MindmapOrganizer] Parent trouvé: '{parent_node.label}' "
                                          f"(position: {parent_node.position_x}, {parent_node.position_y})")
                                # Compter les enfants existants pour positionner
                                children = [n for n in existing_nodes if n.parent_id == suggestion.parent_id]
                                logger.info(f"[MindmapOrganizer] {len(children)} enfants existants pour ce parent")
                                position_x = parent_node.position_x + 200
                                position_y = parent_node.position_y + (len(children) * 80)
                            else:
                                logger.warning(f"[MindmapOrganizer] Parent ID={suggestion.parent_id} non trouvé, "
                                             f"création d'un nœud racine à la place")
                                suggestion.parent_id = None
                        else:
                            # Nœud racine - vérifier s'il y en a déjà un
                            root_nodes = [n for n in existing_nodes if n.is_root]
                            if root_nodes:
                                logger.info(f"[MindmapOrganizer] Nœud racine existant trouvé, "
                                          f"rattachement au nœud '{root_nodes[0].label}' (ID={root_nodes[0].id})")
                                # Rattacher au premier nœud racine
                                suggestion.parent_id = root_nodes[0].id
                                position_x = root_nodes[0].position_x + 200
                                children = [n for n in existing_nodes if n.parent_id == root_nodes[0].id]
                                position_y = root_nodes[0].position_y + (len(children) * 80)
                        
                        logger.info(f"[MindmapOrganizer] Création du nœud avec: "
                                  f"label='{suggestion.label[:50]}', parent_id={suggestion.parent_id}, "
                                  f"position=({position_x}, {position_y})")
                        
                        node_create = NodeCreate(
                            mindmap_id=mindmap_id,
                            parent_id=suggestion.parent_id,
                            label=suggestion.label[:50],  # Limiter la longueur
                            description=suggestion.description,
                            position_x=position_x,
                            position_y=position_y,
                            is_root=suggestion.parent_id is None and not existing_nodes,
                        )
                        
                        try:
                            new_node = create_node(db, node_create)
                            logger.info(f"[MindmapOrganizer] ✅ Nœud créé avec succès: ID={new_node.id}, "
                                      f"label='{new_node.label}', parent_id={new_node.parent_id}")
                            created_nodes.append({
                                "id": new_node.id,
                                "label": new_node.label,
                                "parent_id": new_node.parent_id,
                            })
                            # Mettre à jour le map pour les futures références
                            label_to_id_map[new_node.label.lower()] = new_node.id
                            # Mettre à jour la liste pour les prochaines itérations
                            existing_nodes.append(new_node)
                        except Exception as e:
                            logger.error(f"[MindmapOrganizer] ❌ Erreur lors de la création du nœud: {e}")
                            raise
                    
                    elif suggestion.action == "update" and suggestion.node_id:
                        logger.info(f"[MindmapOrganizer] Mise à jour du nœud ID={suggestion.node_id}")
                        # Mettre à jour un nœud existant
                        node_update = NodeUpdate(
                            label=suggestion.label[:50],
                            description=suggestion.description,
                        )
                        updated = update_node(db, suggestion.node_id, user_id, node_update)
                        if updated:
                            logger.info(f"[MindmapOrganizer] ✅ Nœud mis à jour: ID={updated.id}, label='{updated.label}'")
                            updated_nodes.append({
                                "id": updated.id,
                                "label": updated.label,
                            })
                        else:
                            logger.warning(f"[MindmapOrganizer] ⚠️ Nœud ID={suggestion.node_id} non trouvé pour mise à jour")
            
            logger.info(f"[MindmapOrganizer] ✅ Exécution terminée: {len(created_nodes)} nœuds créés, "
                      f"{len(updated_nodes)} nœuds mis à jour")
            
            return AgentResponse(
                success=True,
                message=result.summary,
                data={
                    "suggestions": [s.model_dump() for s in result.suggestions],
                    "created_nodes": created_nodes,
                    "updated_nodes": updated_nodes,
                    "auto_applied": auto_apply,
                },
            )
            
        except Exception as e:
            logger.error(f"[MindmapOrganizer] ❌ Erreur lors de l'exécution: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                message="Erreur lors de l'exécution de l'agent",
                error=str(e),
            )


# Instance singleton
mindmap_organizer = MindmapOrganizerAgent()
