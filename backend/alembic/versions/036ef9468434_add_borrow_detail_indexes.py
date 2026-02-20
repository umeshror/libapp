"""add_borrow_detail_indexes

Revision ID: 036ef9468434
Revises: ad79da468ca0
Create Date: 2026-02-20 10:41:14.571092

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '036ef9468434'
down_revision = 'ad79da468ca0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f('ix_borrow_record_book_id'), 'borrow_record', ['book_id'], unique=False)
    op.create_index(op.f('ix_borrow_record_returned_at'), 'borrow_record', ['returned_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_borrow_record_returned_at'), table_name='borrow_record')
    op.drop_index(op.f('ix_borrow_record_book_id'), table_name='borrow_record')
