from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Mindmap(Base):
    __tablename__ = "mindmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="mindmaps")
    nodes = relationship("Node", back_populates="mindmap", cascade="all, delete-orphan", order_by="Node.position_x")


class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    mindmap_id = Column(Integer, ForeignKey("mindmaps.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("nodes.id"), nullable=True, index=True)
    
    # Données du nœud
    label = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String, default="#00D9FF")
    position_x = Column(Integer, nullable=False)
    position_y = Column(Integer, nullable=False)
    
    # Statut
    status = Column(String, default="idle")  # idle, active, completed, error
    is_root = Column(Boolean, default=False)
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    mindmap = relationship("Mindmap", back_populates="nodes")
    parent = relationship("Node", remote_side=[id], back_populates="children")
    # Note: Pas de cascade="delete-orphan" sur children pour permettre la réassignation lors de la suppression du parent
    # Utiliser lazy="select" au lieu de "dynamic" pour éviter les problèmes d'accès
    children = relationship("Node", back_populates="parent", lazy="select", cascade="save-update, merge")
    triggers = relationship("Trigger", back_populates="node", cascade="all, delete-orphan")


class Trigger(Base):
    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    
    # Données du trigger
    trigger_type = Column(String, nullable=False)  # email_received, date_reached, cron, state_changed, manual
    enabled = Column(Boolean, default=True)
    config = Column(JSON, nullable=True)  # Configuration spécifique au type de trigger
    
    # Colonnes ajoutées
    last_fired_at = Column(String, nullable=True)
    dedupe_key = Column(String, nullable=True)

    # Relations
    node = relationship("Node", back_populates="triggers")
    actions = relationship("Action", back_populates="trigger", cascade="all, delete-orphan", order_by="Action.order")


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    trigger_id = Column(Integer, ForeignKey("triggers.id"), nullable=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=True, index=True)
    
    # Données de l'action
    name = Column(String, nullable=True)
    action_type = Column(String, nullable=True)  # Utilise action_type au lieu de type (migration ec00d1f3fbe1)
    mode = Column(String, nullable=True)  # Mode d'exécution (auto, review, manual)
    order = Column(Integer, default=0)  # Ordre d'exécution
    enabled = Column(Boolean, default=True)
    config = Column(JSON, nullable=True)  # Configuration spécifique au type d'action (pour email: to, subject, body, etc.)
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    trigger = relationship("Trigger", back_populates="actions")
