"""Add v2 memory tables

Revision ID: 004
Revises: 003
Create Date: 2026-01-06 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create memories_v2 table
    op.create_table(
        'memories_v2',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('scope_type', sa.String(50), nullable=False),
        sa.Column('scope_id', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('truth_mode', sa.String(50), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('sensitivity_level', sa.String(50), nullable=False),
        sa.Column('sensitivity_categories', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('dispute_state', sa.String(50), nullable=False),
        sa.Column('occurred_at_observed', sa.DateTime(), nullable=False),
        sa.Column('occurred_at_claimed', sa.DateTime(), nullable=True),
        sa.Column('strength_current', sa.Numeric(3, 2), nullable=False, server_default='0.75'),
        sa.Column('last_reinforced_at', sa.DateTime(), nullable=True),
        sa.Column('memory_object_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('app_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id']),
    )
    
    # Create indexes for memories_v2
    op.create_index('idx_memories_v2_tenant_id', 'memories_v2', ['tenant_id'])
    op.create_index('idx_memories_v2_scope_type', 'memories_v2', ['scope_type'])
    op.create_index('idx_memories_v2_scope_id', 'memories_v2', ['scope_id'])
    op.create_index('idx_memories_v2_type', 'memories_v2', ['type'])
    op.create_index('idx_memories_v2_truth_mode', 'memories_v2', ['truth_mode'])
    op.create_index('idx_memories_v2_state', 'memories_v2', ['state'])
    op.create_index('idx_memories_v2_sensitivity_level', 'memories_v2', ['sensitivity_level'])
    op.create_index('idx_memories_v2_dispute_state', 'memories_v2', ['dispute_state'])
    op.create_index('idx_memories_v2_occurred_at_observed', 'memories_v2', ['occurred_at_observed'])
    op.create_index('idx_memories_v2_created_at', 'memories_v2', ['created_at'])
    op.create_index('idx_memories_v2_app_id', 'memories_v2', ['app_id'])
    op.create_index('idx_memories_v2_tenant_scope', 'memories_v2', ['tenant_id', 'scope_type', 'scope_id'])
    op.create_index('idx_memories_v2_state_type', 'memories_v2', ['state', 'type'])
    
    # Create memory_links_v2 table
    op.create_table(
        'memory_links_v2',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('parent_id', sa.String(255), nullable=False),
        sa.Column('child_id', sa.String(255), nullable=False),
        sa.Column('relationship', sa.String(50), nullable=False),
        sa.Column('rule', sa.String(255), nullable=False),
        sa.Column('strength_transfer', sa.Numeric(3, 2), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    op.create_index('idx_memory_links_v2_parent', 'memory_links_v2', ['parent_id'])
    op.create_index('idx_memory_links_v2_child', 'memory_links_v2', ['child_id'])
    op.create_index('idx_memory_links_v2_relationship', 'memory_links_v2', ['relationship'])
    
    # Create access_logs_v2 table
    op.create_table(
        'access_logs_v2',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('log_id', sa.String(255), unique=True, nullable=False),
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('caller_client_id', sa.String(255), nullable=True),
        sa.Column('caller_user_id', sa.String(255), nullable=True),
        sa.Column('caller_ip', sa.String(45), nullable=True),
        sa.Column('scope_type', sa.String(50), nullable=False),
        sa.Column('scope_id', sa.String(255), nullable=False),
        sa.Column('purpose', sa.String(50), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=True),
        sa.Column('query_op', sa.String(50), nullable=True),
        sa.Column('decision_allowed', sa.Boolean(), nullable=False),
        sa.Column('decision_returned_ids', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('decision_denied_ids', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('decision_matched_rules', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('decision_explanation', sa.Text(), nullable=True),
        sa.Column('access_log_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    op.create_index('idx_access_logs_v2_log_id', 'access_logs_v2', ['log_id'])
    op.create_index('idx_access_logs_v2_time', 'access_logs_v2', ['time'])
    op.create_index('idx_access_logs_v2_tenant_id', 'access_logs_v2', ['tenant_id'])
    op.create_index('idx_access_logs_v2_caller_user_id', 'access_logs_v2', ['caller_user_id'])
    op.create_index('idx_access_logs_v2_purpose', 'access_logs_v2', ['purpose'])
    op.create_index('idx_access_logs_v2_tenant_time', 'access_logs_v2', ['tenant_id', 'time'])
    op.create_index('idx_access_logs_v2_scope', 'access_logs_v2', ['scope_type', 'scope_id'])
    
    # Create spiral_artifacts_v2 table
    op.create_table(
        'spiral_artifacts_v2',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('scope_type', sa.String(50), nullable=False),
        sa.Column('scope_id', sa.String(255), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Numeric(3, 2), nullable=False, server_default='0.0'),
        sa.Column('signals', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('window_start', sa.DateTime(), nullable=False),
        sa.Column('window_end', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('artifact_json', postgresql.JSONB(), nullable=False),
    )
    
    op.create_index('idx_spiral_artifacts_v2_tenant_id', 'spiral_artifacts_v2', ['tenant_id'])
    op.create_index('idx_spiral_artifacts_v2_created_at', 'spiral_artifacts_v2', ['created_at'])
    op.create_index('idx_spiral_artifacts_v2_expires_at', 'spiral_artifacts_v2', ['expires_at'])
    op.create_index('idx_spiral_artifacts_v2_pattern_type', 'spiral_artifacts_v2', ['pattern_type'])
    op.create_index('idx_spiral_artifacts_v2_tenant_scope', 'spiral_artifacts_v2', ['tenant_id', 'scope_type', 'scope_id'])


def downgrade() -> None:
    op.drop_table('spiral_artifacts_v2')
    op.drop_table('access_logs_v2')
    op.drop_table('memory_links_v2')
    op.drop_table('memories_v2')

