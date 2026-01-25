"""add_due_date_to_nodes

Revision ID: add_due_date_nodes
Revises: a99929a6dced
Create Date: 2026-01-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'add_due_date_nodes'
down_revision = 'a99929a6dced'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter la colonne due_date à la table nodes
    op.add_column('nodes', 
                  sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Supprimer la colonne due_date
    op.drop_column('nodes', 'due_date')
