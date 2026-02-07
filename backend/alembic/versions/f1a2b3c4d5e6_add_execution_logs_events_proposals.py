"""Add execution_logs, events, proposals tables

Revision ID: f1a2b3c4d5e6
Revises: ec00d1f3fbe1
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'ec00d1f3fbe1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Créer l'enum ExecutionStatus s'il n'existe pas
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE executionstatus AS ENUM ('success', 'failed', 'skipped', 'needs_review');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    # Créer l'enum EventType s'il n'existe pas
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE eventtype AS ENUM (
                'TextIngested', 'EmailReceived', 'DateReached',
                'CronTick', 'NodeStateChanged'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    # Créer l'enum ProposalStatus s'il n'existe pas
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE proposalstatus AS ENUM ('pending', 'approved', 'rejected', 'applied');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Table events
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', postgresql.ENUM(
            'TextIngested', 'EmailReceived', 'DateReached', 'CronTick', 'NodeStateChanged',
            name='eventtype', create_type=False
        ), nullable=False),
        sa.Column('idempotency_key', sa.String(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_unique_constraint('uq_events_event_id', 'events', ['event_id'])
    op.create_unique_constraint('uq_events_idempotency', 'events', ['event_type', 'idempotency_key'])

    # Table proposals (node_id Integer pour correspondre à nodes.id)
    op.create_table(
        'proposals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('node_id', sa.Integer(), sa.ForeignKey('nodes.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('agent_name', sa.String(), nullable=False),
        sa.Column('proposal_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', postgresql.ENUM(
            'pending', 'approved', 'rejected', 'applied',
            name='proposalstatus', create_type=False
        ), nullable=False),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Table execution_logs
    op.create_table(
        'execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('node_id', sa.Integer(), sa.ForeignKey('nodes.id'), nullable=True),
        sa.Column('trigger_id', sa.Integer(), sa.ForeignKey('triggers.id'), nullable=True),
        sa.Column('action_id', sa.Integer(), sa.ForeignKey('actions.id'), nullable=True),
        sa.Column('proposal_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('proposals.id'), nullable=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id'), nullable=True),
        sa.Column('idempotency_key', sa.String(), nullable=True),
        sa.Column('status', postgresql.ENUM(
            'success', 'failed', 'skipped', 'needs_review',
            name='executionstatus', create_type=False
        ), nullable=False, server_default='success'),
        sa.Column('input_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('output_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('execution_logs')
    op.drop_table('proposals')
    op.drop_constraint('uq_events_idempotency', 'events', type_='unique')
    op.drop_constraint('uq_events_event_id', 'events', type_='unique')
    op.drop_table('events')
