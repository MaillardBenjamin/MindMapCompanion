"""add_title_and_type_columns_to_nodes

Revision ID: dddba3d71f28
Revises: 8f682b7af22f
Create Date: 2026-01-25 23:04:28.816285

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dddba3d71f28'
down_revision = '8f682b7af22f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Créer le type enum NodeType s'il n'existe pas
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'nodetype') THEN
                CREATE TYPE nodetype AS ENUM ('idea', 'task', 'note', 'project', 'event');
            END IF;
        END $$;
    """)
    
    # Créer le type enum NodeSource s'il n'existe pas
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'nodesource') THEN
                CREATE TYPE nodesource AS ENUM ('ui', 'email', 'api');
            END IF;
        END $$;
    """)
    
    # Créer le type enum NodeStatus s'il n'existe pas
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'nodestatus') THEN
                CREATE TYPE nodestatus AS ENUM ('inbox', 'clarify', 'ready', 'doing', 'waiting', 'done');
            END IF;
        END $$;
    """)
    
    # Ajouter la colonne title si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='title'
            ) THEN
                -- Ajouter la colonne title comme nullable
                ALTER TABLE nodes ADD COLUMN title VARCHAR;
                -- Mettre à jour les lignes existantes : utiliser label si disponible comme titre
                UPDATE nodes 
                SET title = label 
                WHERE title IS NULL AND label IS NOT NULL;
            END IF;
        END $$;
    """)
    
    # Ajouter la colonne type si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='type'
            ) THEN
                -- Ajouter la colonne type comme nullable avec l'enum
                ALTER TABLE nodes ADD COLUMN type nodetype;
            END IF;
        END $$;
    """)
    
    # Ajouter la colonne source si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='source'
            ) THEN
                -- Ajouter la colonne source avec une valeur par défaut
                ALTER TABLE nodes ADD COLUMN source nodesource NOT NULL DEFAULT 'ui';
            END IF;
        END $$;
    """)
    
    # Ajouter la colonne source_ref si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='source_ref'
            ) THEN
                -- Ajouter la colonne source_ref comme JSONB avec valeur par défaut
                ALTER TABLE nodes ADD COLUMN source_ref JSONB NOT NULL DEFAULT '{}'::jsonb;
            END IF;
        END $$;
    """)
    
    # Ajouter la colonne position si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='position'
            ) THEN
                -- Ajouter la colonne position comme JSONB avec valeur par défaut
                ALTER TABLE nodes ADD COLUMN position JSONB NOT NULL DEFAULT '{}'::jsonb;
            END IF;
        END $$;
    """)
    
    # Ajouter la colonne ai_meta si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='ai_meta'
            ) THEN
                -- Ajouter la colonne ai_meta comme JSONB avec valeur par défaut
                ALTER TABLE nodes ADD COLUMN ai_meta JSONB NOT NULL DEFAULT '{}'::jsonb;
            END IF;
        END $$;
    """)
    
    # Mettre à jour la colonne status pour utiliser l'enum si elle existe déjà comme VARCHAR
    op.execute("""
        DO $$ 
        BEGIN
            -- Vérifier si la colonne status existe et est de type VARCHAR
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='status' AND data_type='character varying'
            ) THEN
                -- Convertir la colonne status en enum nodestatus
                ALTER TABLE nodes ALTER COLUMN status TYPE nodestatus USING status::nodestatus;
                -- Ajouter une valeur par défaut si elle n'existe pas
                ALTER TABLE nodes ALTER COLUMN status SET DEFAULT 'inbox'::nodestatus;
            ELSIF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='status'
            ) THEN
                -- Créer la colonne status si elle n'existe pas
                ALTER TABLE nodes ADD COLUMN status nodestatus NOT NULL DEFAULT 'inbox'::nodestatus;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Supprimer la colonne type
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='type'
            ) THEN
                ALTER TABLE nodes DROP COLUMN type;
            END IF;
        END $$;
    """)
    
    # Supprimer la colonne title
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='nodes' AND column_name='title'
            ) THEN
                ALTER TABLE nodes DROP COLUMN title;
            END IF;
        END $$;
    """)
    
    # Note: On ne supprime pas le type enum nodetype car il pourrait être utilisé ailleurs
