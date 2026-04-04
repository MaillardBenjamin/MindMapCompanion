import logging
from sqlalchemy.orm import Session
from typing import List, Optional, Set
from app.models.mindmap import Mindmap, Node, Trigger, Action
from app.schemas.mindmap import MindmapCreate, MindmapUpdate, NodeCreate, NodeUpdate, TriggerCreate, TriggerUpdate, ActionCreate, ActionUpdate

logger = logging.getLogger(__name__)


# ============================================
# Fonctions utilitaires pour la hiérarchie
# ============================================

def _detect_cycle(db: Session, node_id: int, new_parent_id: int, mindmap_id: int) -> bool:
    """
    Détecte si changer le parent d'un nœud créerait un cycle.
    
    Un cycle serait créé si:
    1. Le nouveau parent est le nœud lui-même (node_id == new_parent_id)
    2. Le nouveau parent est un descendant du nœud (le nœud serait son propre ancêtre)
    
    Retourne True si un cycle serait créé, False sinon.
    """
    if new_parent_id is None:
        return False
    
    if node_id == new_parent_id:
        logger.warning(f"[CRUD] Cycle détecté: le nœud {node_id} ne peut pas être son propre parent")
        return True
    
    # Vérifier si le nouveau parent est un descendant du nœud qu'on modifie
    # Si oui, créer un lien créerait un cycle : nœud -> ... -> nouveau_parent -> nœud
    descendants = _get_all_descendants(db, node_id, mindmap_id)
    if new_parent_id in descendants:
        logger.warning(f"[CRUD] Cycle détecté: le nouveau parent {new_parent_id} est un descendant du nœud {node_id}")
        return True
    
    # Vérifier aussi si le nœud est un ancêtre du nouveau parent
    # Parcourir les ancêtres du nouveau parent pour voir si on rencontre le nœud
    # Mais on doit éviter de suivre les cycles existants (ils ne sont pas notre problème)
    visited: Set[int] = set()
    current_id = new_parent_id
    max_depth = 100  # Limite de profondeur pour éviter les boucles infinies
    
    while current_id is not None and len(visited) < max_depth:
        # Protection contre les boucles infinies (cycles existants dans la DB)
        if current_id in visited:
            # C'est un cycle existant dans la hiérarchie, mais ce n'est pas notre problème
            # On s'arrête ici et on considère qu'on n'a pas trouvé le nœud dans les ancêtres
            logger.debug(f"[CRUD] Cycle existant détecté dans la hiérarchie (ignoré): visited={visited}")
            break
        
        visited.add(current_id)
        
        # Si on rencontre le nœud qu'on modifie, il serait son propre ancêtre (cycle)
        if current_id == node_id:
            logger.warning(f"[CRUD] Cycle détecté: le nœud {node_id} serait son propre ancêtre via {new_parent_id}")
            return True
        
        parent_node = db.query(Node).filter(
            Node.id == current_id,
            Node.mindmap_id == mindmap_id
        ).first()
        
        if parent_node is None:
            break
        
        current_id = parent_node.parent_id
    
    return False


def _validate_parent_id(db: Session, parent_id: Optional[int], mindmap_id: int, node_id: Optional[int] = None) -> tuple[bool, str]:
    """
    Valide que le parent_id est valide pour un nœud dans un mindmap donné.
    
    Returns:
        (is_valid, error_message)
    """
    if parent_id is None:
        return True, ""
    
    # Vérifier que le parent existe et appartient au même mindmap
    parent_node = db.query(Node).filter(
        Node.id == parent_id,
        Node.mindmap_id == mindmap_id
    ).first()
    
    if parent_node is None:
        return False, f"Le parent (ID={parent_id}) n'existe pas ou n'appartient pas à ce mindmap"
    
    # Si on modifie un nœud existant, vérifier qu'on ne crée pas un cycle
    if node_id is not None:
        if _detect_cycle(db, node_id, parent_id, mindmap_id):
            return False, f"Changer le parent créerait un cycle dans la hiérarchie"
    
    return True, ""


def _get_all_descendants(db: Session, node_id: int, mindmap_id: int) -> List[int]:
    """
    Récupère tous les IDs des descendants d'un nœud (enfants, petits-enfants, etc.)
    """
    descendants = []
    to_visit = [node_id]
    visited = set()
    
    while to_visit:
        current_id = to_visit.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        
        children = db.query(Node).filter(
            Node.parent_id == current_id,
            Node.mindmap_id == mindmap_id
        ).all()
        
        for child in children:
            if child.id not in visited:
                descendants.append(child.id)
                to_visit.append(child.id)
    
    return descendants


# CRUD pour Mindmap
def create_mindmap(db: Session, user_id: int, mindmap: MindmapCreate) -> Mindmap:
    """Crée un nouveau mindmap pour un utilisateur avec un nœud racine"""
    db_mindmap = Mindmap(
        user_id=user_id,
        name=mindmap.name,
        description=mindmap.description,
    )
    db.add(db_mindmap)
    db.flush()  # Flush pour obtenir l'ID du mindmap
    
    # Créer automatiquement un nœud racine pour le nouveau mindmap
    root_node = Node(
        mindmap_id=db_mindmap.id,
        parent_id=None,
        label=mindmap.name or "Nouveau Mindmap",
        description=mindmap.description,
        color="#00D9FF",
        position_x=400,  # Position centrée par défaut
        position_y=300,
        is_root=True,
        status="idle",
    )
    db.add(root_node)
    db.commit()
    db.refresh(db_mindmap)
    logger.info(f"[CRUD] ✅ create_mindmap - Mindmap créé: ID={db_mindmap.id}, nœud racine créé: ID={root_node.id}")
    return db_mindmap


def get_mindmap(db: Session, mindmap_id: int, user_id: int) -> Mindmap:
    """Récupère un mindmap par ID (vérifie que l'utilisateur est propriétaire)"""
    return db.query(Mindmap).filter(
        Mindmap.id == mindmap_id,
        Mindmap.user_id == user_id
    ).first()


def get_mindmaps_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Mindmap]:
    """Récupère tous les mindmaps d'un utilisateur"""
    return db.query(Mindmap).filter(
        Mindmap.user_id == user_id,
        Mindmap.is_active == True
    ).offset(skip).limit(limit).all()


def update_mindmap(db: Session, mindmap_id: int, user_id: int, mindmap_update: MindmapUpdate) -> Mindmap:
    """Met à jour un mindmap"""
    db_mindmap = get_mindmap(db, mindmap_id, user_id)
    if not db_mindmap:
        return None
    
    update_data = mindmap_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_mindmap, field, value)
    
    db.commit()
    db.refresh(db_mindmap)
    return db_mindmap


def delete_mindmap(db: Session, mindmap_id: int, user_id: int) -> bool:
    """Supprime un mindmap (soft delete)"""
    db_mindmap = get_mindmap(db, mindmap_id, user_id)
    if not db_mindmap:
        return False
    
    db_mindmap.is_active = False
    db.commit()
    return True


# CRUD pour Node
def create_node(db: Session, node: NodeCreate) -> Node:
    """Crée un nouveau nœud avec validation du parent"""
    logger.info(f"[CRUD] create_node - mindmap_id={node.mindmap_id}, parent_id={node.parent_id}, "
              f"label='{node.label}', description='{node.description[:50] if node.description else None}...', "
              f"position=({node.position_x}, {node.position_y}), is_root={node.is_root}")
    
    # Valider le parent_id
    if node.parent_id is not None:
        is_valid, error_msg = _validate_parent_id(db, node.parent_id, node.mindmap_id)
        if not is_valid:
            logger.error(f"[CRUD] ❌ create_node - Validation échouée: {error_msg}")
            raise ValueError(error_msg)
    
    # Si c'est un nœud racine, vérifier qu'il n'y a pas de parent
    if node.is_root and node.parent_id is not None:
        logger.warning(f"[CRUD] ⚠️ create_node - is_root=True mais parent_id={node.parent_id}, correction automatique")
        node_parent_id = None
    else:
        node_parent_id = node.parent_id
    
    db_node = Node(
        mindmap_id=node.mindmap_id,
        parent_id=node_parent_id,
        label=node.label,
        description=node.description,
        color=node.color,
        position_x=node.position_x,
        position_y=node.position_y,
        is_root=node.is_root or (node_parent_id is None),  # Nœud racine si pas de parent
        status=node.status,
    )
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    
    logger.info(f"[CRUD] ✅ create_node - Nœud créé: ID={db_node.id}, label='{db_node.label}', "
              f"parent_id={db_node.parent_id}, is_root={db_node.is_root}")
    return db_node


def get_node(db: Session, node_id: int, user_id: int) -> Node:
    """Récupère un nœud par ID (vérifie que l'utilisateur est propriétaire du mindmap)"""
    return db.query(Node).join(Mindmap).filter(
        Node.id == node_id,
        Mindmap.user_id == user_id
    ).first()


def get_node_by_id(db: Session, node_id: int) -> Optional[Node]:
    """Récupère un nœud par ID sans filtre utilisateur (scheduler / tâches internes)."""
    return db.query(Node).filter(Node.id == node_id).first()


def get_nodes_by_mindmap(db: Session, mindmap_id: int, user_id: int) -> List[Node]:
    """Récupère tous les nœuds d'un mindmap"""
    return db.query(Node).join(Mindmap).filter(
        Node.mindmap_id == mindmap_id,
        Mindmap.user_id == user_id
    ).all()


def update_node(db: Session, node_id: int, user_id: int, node_update: NodeUpdate) -> Node:
    """Met à jour un nœud avec validation des modifications de parent"""
    logger.info(f"[CRUD] update_node - node_id={node_id}, user_id={user_id}, "
              f"updates={node_update.model_dump(exclude_unset=True)}")
    
    db_node = get_node(db, node_id, user_id)
    if not db_node:
        logger.warning(f"[CRUD] ⚠️ update_node - Nœud ID={node_id} non trouvé pour user_id={user_id}")
        return None
    
    update_data = node_update.model_dump(exclude_unset=True)
    
    # Valider le changement de parent_id si demandé
    if 'parent_id' in update_data:
        new_parent_id = update_data['parent_id']
        old_parent_id = db_node.parent_id
        
        # Ne valider que si le parent change vraiment
        if new_parent_id != old_parent_id:
            logger.info(f"[CRUD] update_node - Changement de parent: {old_parent_id} → {new_parent_id}")
            
            # Valider le nouveau parent
            is_valid, error_msg = _validate_parent_id(db, new_parent_id, db_node.mindmap_id, node_id)
            if not is_valid:
                logger.error(f"[CRUD] ❌ update_node - Validation échouée: {error_msg}")
                raise ValueError(error_msg)
            
            # Si le nœud devient racine
            if new_parent_id is None:
                update_data['is_root'] = True
                logger.info(f"[CRUD] update_node - Le nœud devient racine (is_root=True)")
            elif db_node.is_root and new_parent_id is not None:
                update_data['is_root'] = False
                logger.info(f"[CRUD] update_node - Le nœud n'est plus racine (is_root=False)")
    
    # Appliquer les mises à jour
    for field, value in update_data.items():
        old_value = getattr(db_node, field)
        setattr(db_node, field, value)
        if old_value != value:
            logger.debug(f"[CRUD] update_node - {field}: {old_value} → {value}")
    
    db.commit()
    db.refresh(db_node)
    
    logger.info(f"[CRUD] ✅ update_node - Nœud mis à jour: ID={db_node.id}, label='{db_node.label}', "
              f"parent_id={db_node.parent_id}")
    
    return db_node


def delete_node(db: Session, node_id: int, user_id: int, cascade_delete: bool = False) -> dict:
    """
    Supprime un nœud et gère ses enfants.
    
    Args:
        db: Session de base de données
        node_id: ID du nœud à supprimer
        user_id: ID de l'utilisateur
        cascade_delete: Si True, supprime aussi tous les descendants. Si False, les rattache au parent.
    
    Returns:
        dict avec les informations sur la suppression:
        - success: bool
        - deleted_ids: liste des IDs supprimés
        - reassigned_children: liste des enfants réassignés (si cascade_delete=False)
        - error: message d'erreur si échec
    """
    result = {
        "success": False,
        "deleted_ids": [],
        "reassigned_children": [],
        "error": None
    }
    
    db_node = get_node(db, node_id, user_id)
    if not db_node:
        result["error"] = f"Nœud ID={node_id} non trouvé"
        logger.warning(f"[CRUD] ⚠️ delete_node - {result['error']}")
        return result
    
    mindmap_id = db_node.mindmap_id
    node_label = db_node.label
    node_parent_id = db_node.parent_id
    is_root = db_node.is_root
    
    logger.info(f"[CRUD] delete_node - Suppression du nœud {node_id} ('{node_label}'), "
              f"parent_id={node_parent_id}, is_root={is_root}, cascade={cascade_delete}")
    
    # Récupérer tous les enfants directs du nœud (avec query explicite car lazy='dynamic')
    children = db.query(Node).filter(
        Node.parent_id == node_id,
        Node.mindmap_id == mindmap_id
    ).all()
    
    logger.info(f"[CRUD] delete_node - {len(children)} enfants directs trouvés")
    
    if cascade_delete:
        # Supprimer tous les descendants
        all_descendants = _get_all_descendants(db, node_id, mindmap_id)
        logger.info(f"[CRUD] delete_node - Suppression en cascade de {len(all_descendants)} descendants")
        
        # Supprimer les descendants du plus profond au moins profond
        for desc_id in reversed(all_descendants):
            desc_node = db.query(Node).filter(Node.id == desc_id).first()
            if desc_node:
                logger.info(f"[CRUD] delete_node - Suppression du descendant {desc_id} ('{desc_node.label}')")
                db.delete(desc_node)
                result["deleted_ids"].append(desc_id)
        
        db.flush()
    else:
        # Réassigner les enfants au parent du nœud supprimé
        if children:
            new_parent_id = node_parent_id  # Parent du nœud qu'on supprime
            
            if new_parent_id is None:
                # Le nœud supprimé est une racine, chercher un autre nœud racine
                other_root = db.query(Node).filter(
                    Node.mindmap_id == mindmap_id,
                    Node.id != node_id,
                    (Node.parent_id == None) | (Node.is_root == True)
                ).first()
                
                if other_root:
                    new_parent_id = other_root.id
                    logger.info(f"[CRUD] delete_node - Nœud racine supprimé, rattachement des enfants à {other_root.id} ('{other_root.label}')")
            
            for child in children:
                old_parent = child.parent_id
                child.parent_id = new_parent_id
                
                # Si le nouveau parent est None, l'enfant devient racine
                if new_parent_id is None:
                    child.is_root = True
                
                result["reassigned_children"].append({
                    "id": child.id,
                    "label": child.label,
                    "old_parent_id": old_parent,
                    "new_parent_id": new_parent_id
                })
                logger.info(f"[CRUD] delete_node - Enfant {child.id} ('{child.label}') "
                          f"réassigné: {old_parent} → {new_parent_id}")
            
            db.flush()  # Appliquer les changements de parent_id AVANT la suppression
    
    # Supprimer le nœud principal
    db.delete(db_node)
    result["deleted_ids"].insert(0, node_id)
    
    try:
        db.commit()
        result["success"] = True
        logger.info(f"[CRUD] ✅ delete_node - Nœud {node_id} supprimé avec succès. "
                  f"Enfants réassignés: {len(result['reassigned_children'])}")
    except Exception as e:
        db.rollback()
        result["error"] = str(e)
        logger.error(f"[CRUD] ❌ delete_node - Erreur lors du commit: {e}")
    
    return result


# CRUD pour Trigger
def create_trigger(db: Session, trigger: TriggerCreate, user_id: int) -> Trigger:
    """Crée un nouveau trigger (vérifie que l'utilisateur est propriétaire du node)"""
    # Vérifier que le node appartient à l'utilisateur
    db_node = get_node(db, trigger.node_id, user_id)
    if not db_node:
        return None
    
    db_trigger = Trigger(
        node_id=trigger.node_id,
        trigger_type=trigger.trigger_type,
        enabled=trigger.enabled,
        config=trigger.config or {},
    )
    db.add(db_trigger)
    db.commit()
    db.refresh(db_trigger)
    return db_trigger


def get_trigger(db: Session, trigger_id: int, user_id: int) -> Trigger:
    """Récupère un trigger par ID"""
    return db.query(Trigger).join(Node).join(Mindmap).filter(
        Trigger.id == trigger_id,
        Mindmap.user_id == user_id
    ).first()


def get_triggers_by_node(db: Session, node_id: int, user_id: int) -> List[Trigger]:
    """Récupère tous les triggers d'un nœud"""
    return db.query(Trigger).join(Node).join(Mindmap).filter(
        Trigger.node_id == node_id,
        Mindmap.user_id == user_id
    ).all()


def update_trigger(db: Session, trigger_id: int, user_id: int, trigger_update: TriggerUpdate) -> Trigger:
    """Met à jour un trigger"""
    db_trigger = get_trigger(db, trigger_id, user_id)
    if not db_trigger:
        return None
    
    update_data = trigger_update.model_dump(exclude_unset=True)
    previous_config = db_trigger.config or {}
    previous_run_at = previous_config.get("run_at")
    for field, value in update_data.items():
        setattr(db_trigger, field, value)
    
    # Si un trigger "date_reached" est reprogrammé, réinitialiser last_fired_at
    # pour permettre une nouvelle exécution.
    updated_config = update_data.get("config") if isinstance(update_data.get("config"), dict) else None
    updated_run_at = updated_config.get("run_at") if updated_config else None
    updated_trigger_type = update_data.get("trigger_type", db_trigger.trigger_type)
    if updated_trigger_type == "date_reached" and updated_run_at and updated_run_at != previous_run_at:
        db_trigger.last_fired_at = None
    
    db.commit()
    db.refresh(db_trigger)
    return db_trigger


def delete_trigger(db: Session, trigger_id: int, user_id: int) -> bool:
    """Supprime un trigger"""
    db_trigger = get_trigger(db, trigger_id, user_id)
    if not db_trigger:
        return False
    
    db.delete(db_trigger)
    db.commit()
    return True


# CRUD pour Action
def create_action(db: Session, action: ActionCreate, user_id: int) -> Action:
    """Crée une nouvelle action (vérifie que l'utilisateur est propriétaire du trigger)"""
    # Vérifier que le trigger appartient à l'utilisateur
    db_trigger = get_trigger(db, action.trigger_id, user_id)
    if not db_trigger:
        return None
    
    db_action = Action(
        trigger_id=action.trigger_id,
        name=action.name,
        action_type=getattr(action, "action_type", None) or getattr(action, "type", None),
        order=action.order,
        enabled=action.enabled,
        config=action.config,
    )
    db.add(db_action)
    db.commit()
    db.refresh(db_action)
    return db_action


def get_action(db: Session, action_id: int, user_id: int) -> Action:
    """Récupère une action par ID"""
    return db.query(Action).join(Trigger).join(Node).join(Mindmap).filter(
        Action.id == action_id,
        Mindmap.user_id == user_id
    ).first()


def get_actions_by_trigger(db: Session, trigger_id: int, user_id: int) -> List[Action]:
    """Récupère toutes les actions d'un trigger"""
    return db.query(Action).join(Trigger).join(Node).join(Mindmap).filter(
        Action.trigger_id == trigger_id,
        Mindmap.user_id == user_id
    ).order_by(Action.order).all()


def update_action(db: Session, action_id: int, user_id: int, action_update: ActionUpdate) -> Action:
    """Met à jour une action"""
    db_action = get_action(db, action_id, user_id)
    if not db_action:
        return None
    
    update_data = action_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_action, field, value)
    
    db.commit()
    db.refresh(db_action)
    return db_action


def delete_action(db: Session, action_id: int, user_id: int) -> bool:
    """Supprime une action"""
    db_action = get_action(db, action_id, user_id)
    if not db_action:
        return False
    
    db.delete(db_action)
    db.commit()
    return True
