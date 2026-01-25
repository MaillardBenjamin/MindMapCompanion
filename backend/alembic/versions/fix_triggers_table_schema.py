"""Fix triggers table schema - rename type to trigger_type and add missing columns

Revision ID: fix_triggers_schema
Revises: a1b2c3d4e5f6
Create Date: 2026-01-21 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fix_triggers_schema'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Renommer la colonne 'type' en 'trigger_type'
    op.alter_column('triggers', 'type', new_column_name='trigger_type', existing_type=sa.String())
    
    # Créer l'enum TriggerType s'il n'existe pas
    # Note: PostgreSQL crée automatiquement l'enum si on utilise Enum dans SQLAlchemy
    # Mais ici on doit le créer manuellement pour la migration
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE triggertype AS ENUM ('email_received', 'date_reached', 'cron', 'state_changed', 'manual');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Mapper les valeurs invalides vers des valeurs valides avant la conversion
    # "schedule" -> "cron" (ancien nom)
    # Vérifier d'abord si la colonne existe et contient des valeurs
    op.execute("""
        DO $$ 
        BEGIN
            -- Vérifier si la colonne trigger_type existe
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='triggers' AND column_name='trigger_type'
            ) THEN
                -- Convertir "schedule" en "cron"
                UPDATE triggers 
                SET trigger_type = 'cron' 
                WHERE trigger_type = 'schedule';
            END IF;
        END $$;
    """)
    
    # Changer le type de la colonne trigger_type en enum
    # Utiliser une conversion plus sûre avec CASE pour gérer les valeurs inattendues
    op.execute("""
        DO $$ 
        BEGIN
            -- Vérifier si la colonne est encore en VARCHAR
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='triggers' 
                AND column_name='trigger_type' 
                AND data_type='character varying'
            ) THEN
                -- Convertir en enum avec gestion des valeurs invalides
                ALTER TABLE triggers 
                ALTER COLUMN trigger_type TYPE triggertype 
                USING CASE 
                    WHEN trigger_type = 'email_received' THEN 'email_received'::triggertype
                    WHEN trigger_type = 'date_reached' THEN 'date_reached'::triggertype
                    WHEN trigger_type = 'cron' OR trigger_type = 'schedule' THEN 'cron'::triggertype
                    WHEN trigger_type = 'state_changed' THEN 'state_changed'::triggertype
                    WHEN trigger_type = 'manual' THEN 'manual'::triggertype
                    ELSE 'manual'::triggertype  -- Valeur par défaut pour les valeurs inconnues
                END;
            END IF;
        END $$;
    """)
    
    # Changer config de JSON en JSONB
    op.execute("""
        ALTER TABLE triggers 
        ALTER COLUMN config TYPE jsonb 
        USING config::jsonb;
    """)
    
    # Ajouter les colonnes manquantes
    op.add_column('triggers', sa.Column('last_fired_at', sa.String(), nullable=True))
    op.add_column('triggers', sa.Column('dedupe_key', sa.String(), nullable=True))
    
    # Supprimer la colonne 'name' si elle existe (elle n'est pas dans le modèle)
    # On vérifie d'abord si elle existe
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='triggers' AND column_name='name'
            ) THEN
                ALTER TABLE triggers DROP COLUMN name;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Supprimer les colonnes ajoutées
    op.drop_column('triggers', 'dedupe_key')
    op.drop_column('triggers', 'last_fired_at')
    
    # Reconvertir trigger_type en String
    op.execute("""
        ALTER TABLE triggers 
        ALTER COLUMN trigger_type TYPE VARCHAR 
        USING trigger_type::text;
    """)
    
    # Reconvertir config en JSON
    op.execute("""
        ALTER TABLE triggers 
        ALTER COLUMN config TYPE json 
        USING config::json;
    """)
    
    # Renommer trigger_type en type
    op.alter_column('triggers', 'trigger_type', new_column_name='type', existing_type=sa.String())
