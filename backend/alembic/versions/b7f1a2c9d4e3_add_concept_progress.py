"""add concept_progress table and attempts.user_id index

Revision ID: b7f1a2c9d4e3
Revises: d3c2fa012dfc
Create Date: 2026-05-25 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7f1a2c9d4e3'
down_revision: Union[str, Sequence[str], None] = 'd3c2fa012dfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'concept_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('concept_id', sa.Integer(), nullable=False),
        sa.Column('chat_score', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('chat_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'concept_id'),
    )
    op.create_index(
        op.f('ix_concept_progress_user_id'), 'concept_progress', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_attempts_user_id'), 'attempts', ['user_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_attempts_user_id'), table_name='attempts')
    op.drop_index(op.f('ix_concept_progress_user_id'), table_name='concept_progress')
    op.drop_table('concept_progress')
