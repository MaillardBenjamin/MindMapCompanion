"""
Agent MindmapReorganizer: Réorganise la structure du mindmap existant.

Cet agent analyse la structure actuelle du mindmap et propose:
1. Des réorganisations de la hiérarchie
2. Des fusions de nœuds similaires
3. Des renommages pour plus de clarté
4. Des suppressions de doublons
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from agno.agent import Agent

from sqlalchemy.orm import Session

from app.agents.base import AgentBase, AgentResponse

# Logger pour le débogage
logger = logging.getLogger(__name__)
from app.crud.mindmap import (
    get_nodes_by_mindmap,
    update_node,
    delete_node,
    get_node,
    create_node,
    get_triggers_by_node,
    get_actions_by_trigger,
    create_trigger,
    create_action,
)
from app.schemas.mindmap import NodeUpdate, NodeCreate, TriggerCreate, ActionCreate


class ReorganizeAction(BaseModel):
    """Action de réorganisation"""
    action: str  # "move", "rename", "merge", "delete", "create"
    node_id: Optional[int] = None  # Requis sauf pour create
    new_parent_id: Optional[int] = None  # Pour move et create
    new_label: Optional[str] = None  # Pour rename et create
    new_description: Optional[str] = None  # Pour create
    merge_into_id: Optional[int] = None  # Pour merge
    reasoning: str


class ReorganizeResult(BaseModel):
    """Résultat de la réorganisation"""
    actions: List[ReorganizeAction]
    summary: str
    improvements: List[str]  # Liste des améliorations apportées


class MindmapReorganizerAgent(AgentBase):
    """Agent qui réorganise la structure du mindmap"""
    
    @property
    def name(self) -> str:
        return "MindmapReorganizer"
    
    @property
    def description(self) -> str:
        return "Réorganise la structure du mindmap pour une meilleure lisibilité et cohérence"
    
    def _create_agent(self) -> Agent:
        """Crée l'agent Agno pour la réorganisation"""
        return Agent(
            name=self.name,
            model=self.model,
            instructions="""Tu es un expert en organisation de l'information et en optimisation de structures hiérarchiques.

Ton rôle est d'analyser un mindmap existant et de proposer des réorganisations pour améliorer:
- La clarté de la structure
- La cohérence thématique
- L'équilibre de la hiérarchie
- L'élimination des redondances

ACTIONS DISPONIBLES:

1. MOVE: Déplacer un nœud vers un autre parent
   - Utilise quand un nœud serait mieux classé ailleurs
   - Préserve les enfants du nœud déplacé

2. RENAME: Renommer un nœud
   - Utilise pour des titres plus clairs ou cohérents
   - Garde les titres courts (max 30 caractères)

3. MERGE: Fusionner deux nœuds similaires
   - Utilise pour éliminer les doublons
   - Le contenu du nœud source est ajouté à la cible
   - Les enfants sont transférés à la cible
   - ⚠️ ÉVITE de fusionner directement dans un nœud existant si cela crée une hiérarchie plate
   - ✅ PRÉFÈRE créer un nœud intermédiaire si plusieurs nœuds doivent être regroupés sous un thème commun

4. CREATE: Créer un nouveau nœud intermédiaire
   - Utilise pour créer des catégories/thèmes intermédiaires qui améliorent la structure
   - Exemple: Si plusieurs nœuds doivent être regroupés sous "Projets", crée d'abord "Projets" puis déplace les nœuds sous ce nouveau parent
   - Ne fusionne PAS directement dans un nœud existant si cela crée une hiérarchie trop plate
   - Le nouveau nœud doit avoir un label descriptif et un parent_id approprié

5. DELETE: Supprimer un nœud
   - Utilise avec précaution, seulement pour les nœuds vides ou redondants
   - Attention: supprime aussi les enfants

RÈGLES IMPORTANTES:
- Ne jamais supprimer ou déplacer le nœud racine
- Privilégier les petites améliorations plutôt que des restructurations majeures
- Toujours expliquer le raisonnement
- Limiter à 10 actions maximum par exécution
- ⚠️ HIÉRARCHIE: Si plusieurs nœuds doivent être regroupés sous un thème commun qui n'existe pas encore, CRÉE d'abord un nœud intermédiaire avec CREATE, puis déplace les nœuds avec MOVE
- ❌ NE PAS fusionner directement dans un nœud existant si cela crée une hiérarchie trop plate ou mélange des concepts différents

RÉPONDS UNIQUEMENT EN JSON valide, sans texte avant ou après. Format exact requis:
{
    "actions": [
        {
            "action": "move" | "rename" | "merge" | "delete" | "create",
            "node_id": ID du nœud concerné (requis sauf pour create),
            "new_parent_id": ID du nouveau parent (pour move et create),
            "new_label": "Nouveau titre" (pour rename et create),
            "new_description": "Description optionnelle" (pour create uniquement),
            "merge_into_id": ID du nœud cible (pour merge),
            "reasoning": "Explication du choix"
        }
    ],
    "summary": "Résumé des modifications proposées",
    "improvements": ["Amélioration 1", "Amélioration 2", ...]
}

EXEMPLE pour créer un nœud intermédiaire:
Si tu veux regrouper plusieurs nœuds sous "Projets" qui n'existe pas encore:
1. CREATE: {"action": "create", "new_label": "Projets", "new_parent_id": <parent_id>, "reasoning": "Création d'un nœud intermédiaire pour regrouper les projets"}
2. MOVE: {"action": "move", "node_id": <id1>, "new_parent_id": <id_du_nouveau_projets>, "reasoning": "Déplacement sous Projets"}
3. MOVE: {"action": "move", "node_id": <id2>, "new_parent_id": <id_du_nouveau_projets>, "reasoning": "Déplacement sous Projets"}

IMPORTANT: Réponds UNIQUEMENT avec du JSON valide, rien d'autre.
""",
        )
    
    def _build_tree_representation(self, nodes: List[Any]) -> str:
        """Construit une représentation textuelle de l'arbre"""
        if not nodes:
            return "Le mindmap est vide."
        
        # Construire un dictionnaire pour accès rapide
        nodes_dict = {n.id: n for n in nodes}
        
        # Trouver les nœuds racines
        root_nodes = [n for n in nodes if n.is_root or n.parent_id is None]
        
        # Ensemble pour suivre les nœuds visités et détecter les cycles
        visited_nodes = set()
        
        def build_subtree(node, depth=0, visited_path=None) -> str:
            # Protection contre la récursion infinie (cycles)
            if visited_path is None:
                visited_path = set()
            
            # Vérifier si ce nœud est déjà dans le chemin (cycle détecté)
            if node.id in visited_path:
                indent = "  " * depth
                return f"{indent}└── [{node.id}] {node.label} ⚠️ [CYCLE DÉTECTÉ - nœud déjà visité]"
            
            # Limiter la profondeur pour éviter une récursion trop profonde
            if depth > 50:
                indent = "  " * depth
                return f"{indent}└── [{node.id}] {node.label} ⚠️ [Profondeur maximale atteinte]"
            
            # Ajouter ce nœud au chemin visité
            new_visited_path = visited_path.copy()
            new_visited_path.add(node.id)
            visited_nodes.add(node.id)
            
            indent = "  " * depth
            prefix = "└── " if depth > 0 else ""
            
            result = f"{indent}{prefix}[{node.id}] {node.label}"
            if node.description:
                desc_preview = node.description[:50] + "..." if len(node.description) > 50 else node.description
                result += f"\n{indent}    └─ {desc_preview}"
            
            # Ajouter les enfants
            children = [n for n in nodes if n.parent_id == node.id]
            for child in children:
                result += "\n" + build_subtree(child, depth + 1, new_visited_path)
            
            return result
        
        tree = "Structure actuelle du mindmap:\n\n"
        for root in root_nodes:
            tree += build_subtree(root) + "\n\n"
        
        # Afficher les nœuds qui n'ont pas été visités (probablement orphelins ou cycles)
        unvisited = [n for n in nodes if n.id not in visited_nodes]
        if unvisited:
            tree += "\n⚠️ Nœuds non visités (possiblement orphelins ou cycles):\n"
            for node in unvisited:
                tree += f"  [{node.id}] {node.label} (parent_id={node.parent_id})\n"
        
        return tree
    
    async def execute(
        self,
        db: Session,
        mindmap_id: int,
        user_id: int,
        auto_apply: bool = True,
        focus_area: Optional[str] = None,
    ) -> AgentResponse:
        """
        Exécute l'agent pour réorganiser le mindmap.
        
        Args:
            db: Session de base de données
            mindmap_id: ID du mindmap cible
            user_id: ID de l'utilisateur
            auto_apply: Si True, applique automatiquement les actions
            focus_area: Zone spécifique à optimiser (optionnel)
        
        Returns:
            AgentResponse avec les actions proposées et appliquées
        """
        try:
            logger.info(f"[MindmapReorganizer] Début d'exécution - mindmap_id={mindmap_id}, "
                       f"focus_area='{focus_area}', auto_apply={auto_apply}")
            
            # Récupérer les nœuds existants
            existing_nodes = get_nodes_by_mindmap(db, mindmap_id, user_id)
            logger.info(f"[MindmapReorganizer] {len(existing_nodes)} nœuds existants trouvés")
            
            if not existing_nodes:
                logger.info("[MindmapReorganizer] Mindmap vide, aucune réorganisation nécessaire")
                return AgentResponse(
                    success=True,
                    message="Le mindmap est vide, aucune réorganisation nécessaire.",
                    data={"actions": [], "improvements": []},
                )
            
            tree_repr = self._build_tree_representation(existing_nodes)
            logger.debug(f"[MindmapReorganizer] Structure formatée:\n{tree_repr[:500]}...")
            
            # Construire le prompt
            prompt = f"""
{tree_repr}

{f"ZONE À OPTIMISER: {focus_area}" if focus_area else "Analyse l'ensemble du mindmap."}

Analyse cette structure et propose des réorganisations pour l'améliorer.
Concentre-toi sur:
- Les nœuds mal placés dans la hiérarchie
- Les titres peu clairs ou incohérents
- Les potentiels doublons à fusionner
- Les branches déséquilibrées
"""
            
            logger.info(f"[MindmapReorganizer] Envoi du prompt à l'agent IA (longueur: {len(prompt)} caractères)")
            
            # Exécuter l'agent
            response = self.agent.run(prompt)
            
            logger.info(f"[MindmapReorganizer] Réponse reçue de l'agent (longueur: {len(response.content)} caractères)")
            logger.info(f"[MindmapReorganizer] ========== SORTIE COMPLÈTE DU MODÈLE IA ==========")
            logger.info(f"[MindmapReorganizer] {response.content}")
            logger.info(f"[MindmapReorganizer] =================================================")
            
            # Nettoyer le JSON en supprimant les commentaires JavaScript et en corrigeant les erreurs communes
            cleaned_content = response.content
            # Supprimer les commentaires de ligne (// ...)
            cleaned_content = re.sub(r'//.*?$', '', cleaned_content, flags=re.MULTILINE)
            # Supprimer les commentaires de bloc (/* ... */)
            cleaned_content = re.sub(r'/\*.*?\*/', '', cleaned_content, flags=re.DOTALL)
            # Nettoyer les virgules en fin de ligne avant les accolades/fermetures
            cleaned_content = re.sub(r',\s*([}\]])', r'\1', cleaned_content)
            # Corriger les apostrophes simples qui ferment les chaînes JSON : "texte', -> "texte",
            # Utiliser des guillemets doubles pour la chaîne Python pour éviter les conflits avec l'apostrophe
            cleaned_content = re.sub(r":\s*\"([^\"]*?)',([,}\]])", r': "\1",\2', cleaned_content)
            
            # Parser la réponse JSON
            try:
                result_data = json.loads(cleaned_content)
                logger.info(f"[MindmapReorganizer] JSON parsé avec succès: {len(result_data.get('actions', []))} actions")
                result = ReorganizeResult(**result_data)
                
                # Logger chaque action
                for idx, action in enumerate(result.actions):
                    logger.info(f"[MindmapReorganizer] Action {idx+1}: action={action.action}, "
                              f"node_id={action.node_id}, new_parent_id={action.new_parent_id}, "
                              f"new_label='{action.new_label}', merge_into_id={action.merge_into_id}, "
                              f"new_description={action.new_description[:50] if action.new_description else None}...")
                    
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"[MindmapReorganizer] Erreur lors du parsing JSON: {e}")
                logger.error(f"[MindmapReorganizer] Contenu reçu: {response.content[:500]}")
                return AgentResponse(
                    success=False,
                    message="Erreur lors du parsing de la réponse de l'agent",
                    error=str(e),
                )
            
            applied_actions = []
            skipped_actions = []
            
            if auto_apply:
                logger.info(f"[MindmapReorganizer] Application automatique de {len(result.actions)} actions")
                
                # Appliquer les actions
                for idx, action in enumerate(result.actions):
                    node_id_str = str(action.node_id) if action.node_id is not None else "N/A (create)"
                    logger.info(f"[MindmapReorganizer] Traitement action {idx+1}/{len(result.actions)}: "
                              f"action={action.action}, node_id={node_id_str}")
                    try:
                        if action.action == "move" and action.new_parent_id is not None:
                            logger.info(f"[MindmapReorganizer] Déplacement du nœud {action.node_id} vers parent {action.new_parent_id}")
                            # Déplacer le nœud
                            node = get_node(db, action.node_id, user_id)
                            if node and not node.is_root:
                                node_update = NodeUpdate(parent_id=action.new_parent_id)
                                updated = update_node(db, action.node_id, user_id, node_update)
                                if updated:
                                    logger.info(f"[MindmapReorganizer] ✅ Nœud {action.node_id} déplacé vers {action.new_parent_id}")
                                    applied_actions.append({
                                        "action": "move",
                                        "node_id": action.node_id,
                                        "new_parent_id": action.new_parent_id,
                                    })
                                else:
                                    logger.warning(f"[MindmapReorganizer] ⚠️ Échec du déplacement du nœud {action.node_id}")
                                    skipped_actions.append({
                                        "action": action.action,
                                        "node_id": action.node_id,
                                        "reason": "Échec de la mise à jour",
                                    })
                            else:
                                logger.warning(f"[MindmapReorganizer] ⚠️ Nœud {action.node_id} est racine ou inexistant")
                                skipped_actions.append({
                                    "action": action.action,
                                    "node_id": action.node_id,
                                    "reason": "Nœud racine ou inexistant",
                                })
                        
                        elif action.action == "rename" and action.new_label:
                            logger.info(f"[MindmapReorganizer] Renommage du nœud {action.node_id} en '{action.new_label}'")
                            # Renommer le nœud
                            node_update = NodeUpdate(label=action.new_label[:50])
                            updated = update_node(db, action.node_id, user_id, node_update)
                            if updated:
                                logger.info(f"[MindmapReorganizer] ✅ Nœud {action.node_id} renommé en '{action.new_label}'")
                                applied_actions.append({
                                    "action": "rename",
                                    "node_id": action.node_id,
                                    "new_label": action.new_label,
                                })
                            else:
                                logger.warning(f"[MindmapReorganizer] ⚠️ Échec du renommage du nœud {action.node_id}")
                                skipped_actions.append({
                                    "action": action.action,
                                    "node_id": action.node_id,
                                    "reason": "Échec de la mise à jour",
                                })
                        
                        elif action.action == "merge" and action.merge_into_id:
                            logger.info(f"[MindmapReorganizer] Fusion du nœud {action.node_id} dans {action.merge_into_id}")
                            # Fusionner: transférer les enfants, puis supprimer
                            source_node = get_node(db, action.node_id, user_id)
                            target_node = get_node(db, action.merge_into_id, user_id)
                            
                            if source_node and target_node and not source_node.is_root:
                                # Recharger les nœuds depuis la DB pour avoir les valeurs à jour
                                # (car existing_nodes peut être obsolète après les actions précédentes)
                                current_nodes = get_nodes_by_mindmap(db, mindmap_id, user_id)
                                # Transférer les enfants du nœud source vers le nœud cible
                                children = [n for n in current_nodes if n.parent_id == action.node_id]
                                logger.info(f"[MindmapReorganizer] {len(children)} enfants à transférer de {action.node_id} vers {action.merge_into_id}")
                                for child in children:
                                    logger.info(f"[MindmapReorganizer] Transfert de l'enfant {child.id} ({child.label}) vers {action.merge_into_id}")
                                    child_update = NodeUpdate(parent_id=action.merge_into_id)
                                    update_node(db, child.id, user_id, child_update)
                                
                                # Fusionner les descriptions
                                if source_node.description:
                                    new_desc = target_node.description or ""
                                    if new_desc:
                                        new_desc += "\n\n---\n\n"
                                    new_desc += source_node.description
                                    target_update = NodeUpdate(description=new_desc)
                                    update_node(db, action.merge_into_id, user_id, target_update)
                                
                                # Transférer les triggers et actions du nœud source vers le nœud cible
                                source_triggers = get_triggers_by_node(db, action.node_id, user_id)
                                logger.info(f"[MindmapReorganizer] {len(source_triggers)} trigger(s) à transférer du nœud {action.node_id}")
                                
                                for source_trigger in source_triggers:
                                    # Créer le trigger sur le nœud cible
                                    new_trigger = TriggerCreate(
                                        node_id=action.merge_into_id,
                                        trigger_type=getattr(source_trigger, "trigger_type", None) or getattr(source_trigger, "type", None),
                                        enabled=source_trigger.enabled,
                                        config=source_trigger.config,
                                    )
                                    created_trigger = create_trigger(db, new_trigger, user_id)
                                    
                                    if created_trigger:
                                        logger.info(f"[MindmapReorganizer] Trigger '{source_trigger.name}' transféré vers le nœud {action.merge_into_id}")
                                        
                                        # Récupérer les actions du trigger source
                                        source_actions = get_actions_by_trigger(db, source_trigger.id, user_id)
                                        logger.info(f"[MindmapReorganizer] {len(source_actions)} action(s) à transférer du trigger {source_trigger.id}")
                                        
                                        for source_action in source_actions:
                                            # Créer l'action sur le nouveau trigger
                                            new_action = ActionCreate(
                                                trigger_id=created_trigger.id,
                                                name=source_action.name,
                                                action_type=getattr(source_action, "action_type", None) or getattr(source_action, "type", None),
                                                order=source_action.order,
                                                enabled=source_action.enabled,
                                                config=source_action.config,
                                            )
                                            created_action = create_action(db, new_action, user_id)
                                            if created_action:
                                                logger.info(f"[MindmapReorganizer] Action '{source_action.name}' transférée vers le trigger {created_trigger.id}")
                                            else:
                                                logger.warning(f"[MindmapReorganizer] ⚠️ Échec du transfert de l'action '{source_action.name}'")
                                    else:
                                        logger.warning(f"[MindmapReorganizer] ⚠️ Échec du transfert du trigger '{source_trigger.name}'")
                                
                                # Supprimer le nœud source (cela supprimera aussi les triggers et actions en cascade)
                                delete_node(db, action.node_id, user_id)
                                
                                logger.info(f"[MindmapReorganizer] ✅ Nœud {action.node_id} fusionné dans {action.merge_into_id}")
                                applied_actions.append({
                                    "action": "merge",
                                    "node_id": action.node_id,
                                    "merge_into_id": action.merge_into_id,
                                })
                            else:
                                logger.warning(f"[MindmapReorganizer] ⚠️ Fusion impossible: nœud source ou cible invalide")
                                skipped_actions.append({
                                    "action": action.action,
                                    "node_id": action.node_id,
                                    "reason": "Nœud source ou cible invalide",
                                })
                        
                        elif action.action == "create" and action.new_label and action.new_parent_id is not None:
                            logger.info(f"[MindmapReorganizer] Création d'un nouveau nœud: '{action.new_label}' sous parent {action.new_parent_id}")
                            # Créer un nouveau nœud intermédiaire
                            parent_node = get_node(db, action.new_parent_id, user_id)
                            if parent_node:
                                # Calculer la position du nouveau nœud
                                current_nodes = get_nodes_by_mindmap(db, mindmap_id, user_id)
                                children = [n for n in current_nodes if n.parent_id == action.new_parent_id]
                                position_x = parent_node.position_x + 200
                                position_y = parent_node.position_y + (len(children) * 80)
                                
                                node_create = NodeCreate(
                                    mindmap_id=mindmap_id,
                                    parent_id=action.new_parent_id,
                                    label=action.new_label[:50],
                                    description=action.new_description or "",
                                    position_x=position_x,
                                    position_y=position_y,
                                    is_root=False,
                                )
                                
                                new_node = create_node(db, node_create)
                                logger.info(f"[MindmapReorganizer] ✅ Nœud créé: ID={new_node.id}, label='{new_node.label}', parent_id={new_node.parent_id}")
                                applied_actions.append({
                                    "action": "create",
                                    "node_id": new_node.id,
                                    "new_label": action.new_label,
                                    "new_parent_id": action.new_parent_id,
                                })
                            else:
                                logger.warning(f"[MindmapReorganizer] ⚠️ Parent {action.new_parent_id} inexistant")
                                skipped_actions.append({
                                    "action": action.action,
                                    "reason": f"Parent {action.new_parent_id} inexistant",
                                })
                        
                        elif action.action == "delete":
                            logger.info(f"[MindmapReorganizer] Suppression du nœud {action.node_id}")
                            # Supprimer le nœud
                            node = get_node(db, action.node_id, user_id)
                            if node and not node.is_root:
                                delete_node(db, action.node_id, user_id)
                                logger.info(f"[MindmapReorganizer] ✅ Nœud {action.node_id} supprimé")
                                applied_actions.append({
                                    "action": "delete",
                                    "node_id": action.node_id,
                                })
                            else:
                                logger.warning(f"[MindmapReorganizer] ⚠️ Nœud {action.node_id} est racine ou inexistant")
                                skipped_actions.append({
                                    "action": action.action,
                                    "node_id": action.node_id,
                                    "reason": "Nœud racine ou inexistant",
                                })
                    
                    except Exception as e:
                        logger.error(f"[MindmapReorganizer] ❌ Erreur lors du traitement de l'action {action.action} "
                                   f"sur le nœud {action.node_id}: {e}", exc_info=True)
                        skipped_actions.append({
                            "action": action.action,
                            "node_id": action.node_id,
                            "reason": str(e),
                        })
            
            # Vérifier et corriger les nœuds orphelins après toutes les actions
            logger.info("[MindmapReorganizer] Vérification des nœuds orphelins...")
            final_nodes = get_nodes_by_mindmap(db, mindmap_id, user_id)
            root_nodes = [n for n in final_nodes if n.is_root or n.parent_id is None]
            orphan_fixes = []
            
            for node in final_nodes:
                # Ignorer les nœuds racines
                if node.is_root or node.parent_id is None:
                    continue
                
                # Vérifier si le parent existe
                parent_exists = any(n.id == node.parent_id for n in final_nodes)
                
                if not parent_exists:
                    logger.warning(f"[MindmapReorganizer] ⚠️ Nœud orphelin détecté: ID={node.id}, label='{node.label}', "
                                 f"parent_id={node.parent_id} (parent inexistant)")
                    
                    # Rattacher au premier nœud racine disponible
                    if root_nodes:
                        root_id = root_nodes[0].id
                        logger.info(f"[MindmapReorganizer] Rattachement du nœud {node.id} au nœud racine {root_id}")
                        node_update = NodeUpdate(parent_id=root_id)
                        updated = update_node(db, node.id, user_id, node_update)
                        if updated:
                            orphan_fixes.append({
                                "node_id": node.id,
                                "label": node.label,
                                "old_parent_id": node.parent_id,
                                "new_parent_id": root_id,
                            })
                            logger.info(f"[MindmapReorganizer] ✅ Nœud {node.id} rattaché au nœud racine {root_id}")
                        else:
                            logger.error(f"[MindmapReorganizer] ❌ Échec du rattachement du nœud {node.id}")
                    else:
                        logger.error(f"[MindmapReorganizer] ❌ Aucun nœud racine trouvé, impossible de rattacher le nœud {node.id}")
            
            if orphan_fixes:
                logger.info(f"[MindmapReorganizer] {len(orphan_fixes)} nœud(s) orphelin(s) corrigé(s)")
            else:
                logger.info("[MindmapReorganizer] Aucun nœud orphelin détecté")
            
            logger.info(f"[MindmapReorganizer] ✅ Exécution terminée: {len(applied_actions)} actions appliquées, "
                      f"{len(skipped_actions)} actions ignorées, {len(orphan_fixes)} orphelin(s) corrigé(s)")
            
            return AgentResponse(
                success=True,
                message=result.summary,
                data={
                    "proposed_actions": [a.model_dump() for a in result.actions],
                    "applied_actions": applied_actions,
                    "skipped_actions": skipped_actions,
                    "orphan_fixes": orphan_fixes if 'orphan_fixes' in locals() else [],
                    "improvements": result.improvements,
                    "auto_applied": auto_apply,
                },
            )
            
        except Exception as e:
            logger.error(f"[MindmapReorganizer] ❌ Erreur lors de l'exécution: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                message="Erreur lors de l'exécution de l'agent",
                error=str(e),
            )


# Instance singleton
mindmap_reorganizer = MindmapReorganizerAgent()
