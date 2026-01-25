"""add_input_schema_to_configurable_agents

Revision ID: a99929a6dced
Revises: 3ab43fa35c3f
Create Date: 2026-01-23 23:56:42.532417

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a99929a6dced'
down_revision = '3ab43fa35c3f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter la colonne input_schema à la table configurable_agents
    op.add_column('configurable_agents', 
                  sa.Column('input_schema', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Supprimer la colonne input_schema
    op.drop_column('configurable_agents', 'input_schema')
