"""add_node_id_to_actions_table

Revision ID: ec00d1f3fbe1
Revises: dddba3d71f28
Create Date: 2026-01-25 23:13:26.566767

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ec00d1f3fbe1'
down_revision = 'dddba3d71f28'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rendre trigger_id nullable pour permettre les actions liées directement aux nœuds
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='trigger_id' AND is_nullable='NO'
            ) THEN
                ALTER TABLE actions ALTER COLUMN trigger_id DROP NOT NULL;
            END IF;
        END $$;
    """)
    
    # Rendre name nullable pour les nouvelles actions créées via node_id
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='name' AND is_nullable='NO'
            ) THEN
                ALTER TABLE actions ALTER COLUMN name DROP NOT NULL;
            END IF;
        END $$;
    """)
    
    # Rendre type nullable (remplacé par action_type)
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='type' AND is_nullable='NO'
            ) THEN
                ALTER TABLE actions ALTER COLUMN type DROP NOT NULL;
            END IF;
        END $$;
    """)
    
    # Créer les types enum s'ils n'existent pas
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actiontype') THEN
                CREATE TYPE actiontype AS ENUM (
                    'send_email', 'draft_email', 'call_api', 'update_node', 
                    'run_agent', 'notify', 'create_reminder', 'reminder'
                );
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actionmode') THEN
                CREATE TYPE actionmode AS ENUM ('auto', 'review', 'manual');
            END IF;
        END $$;
    """)
    
    # Ajouter la colonne node_id si elle n'existe pas
    # Note: On utilise INTEGER pour correspondre à nodes.id (ancien système mindmap)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='node_id'
            ) THEN
                -- Ajouter la colonne node_id comme INTEGER nullable
                -- Correspond à nodes.id qui est aussi INTEGER
                ALTER TABLE actions ADD COLUMN node_id INTEGER;
            ELSIF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='node_id' AND data_type='uuid'
            ) THEN
                -- Si node_id existe en UUID, le convertir en INTEGER
                -- D'abord supprimer la colonne UUID vide, puis recréer en INTEGER
                ALTER TABLE actions DROP COLUMN node_id;
                ALTER TABLE actions ADD COLUMN node_id INTEGER;
            END IF;
        END $$;
    """)
    
    # Convertir la colonne id de Integer à UUID si nécessaire
    op.execute("""
        DO $$ 
        BEGIN
            -- Vérifier si id est Integer et doit être converti en UUID
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='id' AND data_type='integer'
            ) THEN
                -- Pour l'instant, on garde Integer pour compatibilité
                -- La conversion vers UUID nécessiterait de migrer toutes les données
                -- On peut ajouter un nouveau champ id_uuid si nécessaire
                NULL;
            END IF;
        END $$;
    """)
    
    # Convertir la colonne type de String à ActionType enum si elle existe
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='type' AND data_type='character varying'
            ) THEN
                -- Renommer l'ancienne colonne type en action_type_old
                ALTER TABLE actions RENAME COLUMN type TO action_type_old;
                -- Ajouter la nouvelle colonne action_type avec l'enum
                ALTER TABLE actions ADD COLUMN action_type actiontype;
                -- Copier les valeurs de l'ancienne colonne vers la nouvelle (si possible)
                UPDATE actions 
                SET action_type = action_type_old::actiontype 
                WHERE action_type_old IN (
                    'send_email', 'draft_email', 'call_api', 'update_node', 
                    'run_agent', 'notify', 'create_reminder', 'reminder'
                );
                -- Supprimer l'ancienne colonne
                ALTER TABLE actions DROP COLUMN action_type_old;
            ELSIF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='action_type'
            ) THEN
                -- Créer la colonne action_type si elle n'existe pas
                ALTER TABLE actions ADD COLUMN action_type actiontype;
            END IF;
        END $$;
    """)
    
    # Ajouter la colonne mode si elle n'existe pas
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='mode'
            ) THEN
                ALTER TABLE actions ADD COLUMN mode actionmode NOT NULL DEFAULT 'review';
            END IF;
        END $$;
    """)
    
    # Convertir config de JSON à JSONB si nécessaire
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='config' AND data_type='json'
            ) THEN
                -- Convertir JSON en JSONB
                ALTER TABLE actions ALTER COLUMN config TYPE JSONB USING config::jsonb;
            ELSIF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='config'
            ) THEN
                -- Créer la colonne config si elle n'existe pas
                ALTER TABLE actions ADD COLUMN config JSONB NOT NULL DEFAULT '{}'::jsonb;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Supprimer la colonne node_id
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='actions' AND column_name='node_id'
            ) THEN
                ALTER TABLE actions DROP CONSTRAINT IF EXISTS fk_actions_node_id;
                ALTER TABLE actions DROP COLUMN node_id;
            END IF;
        END $$;
    """)
    
    # Note: On ne supprime pas les types enum car ils pourraient être utilisés ailleurs
