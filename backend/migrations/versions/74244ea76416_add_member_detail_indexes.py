"""add_member_detail_indexes

Revision ID: 74244ea76416
Revises: 036ef9468434
Create Date: 2026-02-20 11:51:45.087732

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '74244ea76416'
down_revision = '036ef9468434'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f('ix_borrow_record_member_id'), 'borrow_record', ['member_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_borrow_record_member_id'), table_name='borrow_record')
