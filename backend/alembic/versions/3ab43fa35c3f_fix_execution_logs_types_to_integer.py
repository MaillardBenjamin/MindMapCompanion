"""fix_execution_logs_types_to_integer

Revision ID: 3ab43fa35c3f
Revises: fix_triggers_schema
Create Date: 2026-01-23 20:32:50.191532

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '3ab43fa35c3f'
down_revision = 'fix_triggers_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Vérifier si la table execution_logs existe avant de la modifier
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    if 'execution_logs' not in tables:
        # La table n'existe pas, on peut passer cette migration
        return
    
    # Supprimer les contraintes de clé étrangère existantes (si elles existent)
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name='execution_logs_node_id_fkey' 
                AND table_name='execution_logs'
            ) THEN
                ALTER TABLE execution_logs DROP CONSTRAINT execution_logs_node_id_fkey;
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name='execution_logs_trigger_id_fkey' 
                AND table_name='execution_logs'
            ) THEN
                ALTER TABLE execution_logs DROP CONSTRAINT execution_logs_trigger_id_fkey;
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name='execution_logs_action_id_fkey' 
                AND table_name='execution_logs'
            ) THEN
                ALTER TABLE execution_logs DROP CONSTRAINT execution_logs_action_id_fkey;
            END IF;
        END $$;
    """)
    
    # Supprimer les données existantes dans ces colonnes car on ne peut pas convertir UUID en Integer
    # (Les données existantes référencent probablement l'ancien système avec UUID)
    op.execute("UPDATE execution_logs SET node_id = NULL WHERE node_id IS NOT NULL")
    op.execute("UPDATE execution_logs SET trigger_id = NULL WHERE trigger_id IS NOT NULL")
    op.execute("UPDATE execution_logs SET action_id = NULL WHERE action_id IS NOT NULL")
    
    # Changer le type des colonnes de UUID à Integer
    # Comme toutes les valeurs sont NULL, on peut simplement changer le type
    # Pour PostgreSQL, on doit utiliser USING avec une conversion explicite
    # Mais comme toutes les valeurs sont NULL, on peut utiliser une conversion simple
    op.execute("""
        DO $$ 
        BEGIN
            -- Vérifier si la colonne existe et est de type UUID
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='execution_logs' 
                AND column_name='node_id' 
                AND data_type='uuid'
            ) THEN
                ALTER TABLE execution_logs 
                ALTER COLUMN node_id TYPE INTEGER 
                USING NULL::INTEGER;
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='execution_logs' 
                AND column_name='trigger_id' 
                AND data_type='uuid'
            ) THEN
                ALTER TABLE execution_logs 
                ALTER COLUMN trigger_id TYPE INTEGER 
                USING NULL::INTEGER;
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='execution_logs' 
                AND column_name='action_id' 
                AND data_type='uuid'
            ) THEN
                ALTER TABLE execution_logs 
                ALTER COLUMN action_id TYPE INTEGER 
                USING NULL::INTEGER;
            END IF;
        END $$;
    """)
    
    # Recréer les contraintes de clé étrangère vers les tables mindmap (Integer)
    # Vérifier que les tables référencées existent avant de créer les contraintes
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='nodes') THEN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name='execution_logs_node_id_fkey' 
                    AND table_name='execution_logs'
                ) THEN
                    ALTER TABLE execution_logs 
                    ADD CONSTRAINT execution_logs_node_id_fkey 
                    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE SET NULL;
                END IF;
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='triggers') THEN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name='execution_logs_trigger_id_fkey' 
                    AND table_name='execution_logs'
                ) THEN
                    ALTER TABLE execution_logs 
                    ADD CONSTRAINT execution_logs_trigger_id_fkey 
                    FOREIGN KEY (trigger_id) REFERENCES triggers(id) ON DELETE SET NULL;
                END IF;
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='actions') THEN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name='execution_logs_action_id_fkey' 
                    AND table_name='execution_logs'
                ) THEN
                    ALTER TABLE execution_logs 
                    ADD CONSTRAINT execution_logs_action_id_fkey 
                    FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE SET NULL;
                END IF;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Supprimer les contraintes de clé étrangère
    op.drop_constraint('execution_logs_node_id_fkey', 'execution_logs', type_='foreignkey')
    op.drop_constraint('execution_logs_trigger_id_fkey', 'execution_logs', type_='foreignkey')
    op.drop_constraint('execution_logs_action_id_fkey', 'execution_logs', type_='foreignkey')
    
    # Supprimer les données existantes
    op.execute("UPDATE execution_logs SET node_id = NULL WHERE node_id IS NOT NULL")
    op.execute("UPDATE execution_logs SET trigger_id = NULL WHERE trigger_id IS NOT NULL")
    op.execute("UPDATE execution_logs SET action_id = NULL WHERE action_id IS NOT NULL")
    
    # Reconvertir en UUID
    op.alter_column('execution_logs', 'node_id',
                    type_=postgresql.UUID(as_uuid=True),
                    postgresql_using='NULL')
    
    op.alter_column('execution_logs', 'trigger_id',
                    type_=postgresql.UUID(as_uuid=True),
                    postgresql_using='NULL')
    
    op.alter_column('execution_logs', 'action_id',
                    type_=postgresql.UUID(as_uuid=True),
                    postgresql_using='NULL')
    
    # Recréer les contraintes de clé étrangère vers les tables UUID (ancien système)
    # Note: Ces contraintes ne fonctionneront probablement pas car les tables référencées n'existent plus
    # mais on les recrée pour la cohérence de la migration
    op.create_foreign_key(
        'execution_logs_node_id_fkey',
        'execution_logs', 'nodes',
        ['node_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'execution_logs_trigger_id_fkey',
        'execution_logs', 'triggers',
        ['trigger_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'execution_logs_action_id_fkey',
        'execution_logs', 'actions',
        ['action_id'], ['id'],
        ondelete='SET NULL'
    )
