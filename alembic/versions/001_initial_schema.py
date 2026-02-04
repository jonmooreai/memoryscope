"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create apps table
    op.create_table(
        'apps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('api_key_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create memories table
    op.create_table(
        'memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('scope', sa.String(50), nullable=False),
        sa.Column('domain', sa.Text(), nullable=True),
        sa.Column('value_json', postgresql.JSONB(), nullable=False),
        sa.Column('value_shape', sa.String(50), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('ttl_days', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('app_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id']),
    )
    op.create_index(
        'idx_memories_user_scope_domain_created',
        'memories',
        ['user_id', 'scope', 'domain', 'created_at'],
    )
    op.create_index('idx_memories_expires_at', 'memories', ['expires_at'])

    # Create read_grants table
    op.create_table(
        'read_grants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('revocation_token_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('app_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scope', sa.String(50), nullable=False),
        sa.Column('domain', sa.Text(), nullable=True),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('purpose_class', sa.String(50), nullable=False),
        sa.Column('max_age_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoke_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id']),
    )

    # Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=True),
        sa.Column('app_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scope', sa.String(50), nullable=True),
        sa.Column('domain', sa.Text(), nullable=True),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('purpose_class', sa.String(50), nullable=True),
        sa.Column('memory_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('revocation_grant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reason_code', sa.String(50), nullable=True),
        sa.Column('meta', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id']),
    )
    op.create_index(
        'idx_audit_user_timestamp',
        'audit_events',
        ['user_id', 'timestamp'],
    )
    op.create_index(
        'idx_audit_app_timestamp',
        'audit_events',
        ['app_id', 'timestamp'],
    )
    op.create_index(
        'idx_audit_event_type_timestamp',
        'audit_events',
        ['event_type', 'timestamp'],
    )


def downgrade() -> None:
    op.drop_index('idx_audit_event_type_timestamp', table_name='audit_events')
    op.drop_index('idx_audit_app_timestamp', table_name='audit_events')
    op.drop_index('idx_audit_user_timestamp', table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_table('read_grants')
    op.drop_index('idx_memories_expires_at', table_name='memories')
    op.drop_index('idx_memories_user_scope_domain_created', table_name='memories')
    op.drop_table('memories')
    op.drop_table('apps')

