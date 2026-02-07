"""add_raw_text_to_nodes

Revision ID: 8f682b7af22f
Revises: add_due_date_nodes
Create Date: 2026-01-25 13:26:24.008079

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f682b7af22f'
down_revision = 'add_due_date_nodes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter la colonne raw_text si elle n'existe pas déjà
    # Utilisation d'une requête SQL conditionnelle pour éviter les erreurs si la colonne existe
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='raw_text'
            ) THEN
                -- Ajouter la colonne avec une valeur par défaut temporaire
                ALTER TABLE nodes ADD COLUMN raw_text VARCHAR NOT NULL DEFAULT '';
                -- Mettre à jour les lignes existantes : utiliser le titre si disponible, sinon une chaîne vide
                UPDATE nodes 
                SET raw_text = COALESCE(title, '') 
                WHERE raw_text = '';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Supprimer la colonne raw_text
    op.drop_column('nodes', 'raw_text')
