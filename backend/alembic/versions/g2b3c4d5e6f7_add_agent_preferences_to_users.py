"""add_agent_preferences_to_users

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = 'g2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('agent_langue', sa.String(10), nullable=False, server_default='fr'))
    op.add_column('users', sa.Column('agent_adresse', sa.String(10), nullable=True))
    op.add_column('users', sa.Column('agent_prenom', sa.String(120), nullable=True))
    op.add_column('users', sa.Column('agent_ton', sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'agent_ton')
    op.drop_column('users', 'agent_prenom')
    op.drop_column('users', 'agent_adresse')
    op.drop_column('users', 'agent_langue')
