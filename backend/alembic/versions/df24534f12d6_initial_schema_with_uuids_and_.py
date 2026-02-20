"""Initial schema with UUIDs and constraints

Revision ID: df24534f12d6
Revises: 
Create Date: 2026-02-19 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'df24534f12d6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop ENUM type if exists to prevent DuplicateObject error
    op.execute("DROP TYPE IF EXISTS borrowstatus CASCADE")
    
    # Create ENUM type
    # borrow_status_enum = postgresql.ENUM('borrowed', 'returned', name='borrowstatus')
    # borrow_status_enum.create(op.get_bind(), checkfirst=True)

    # Create table: book
    op.create_table('book',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('author', sa.String(), nullable=False),
        sa.Column('isbn', sa.String(), nullable=False),
        sa.Column('total_copies', sa.Integer(), nullable=False),
        sa.Column('available_copies', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('total_copies >= 0', name='check_total_copies_non_negative'),
        sa.CheckConstraint('available_copies >= 0', name='check_available_copies_non_negative')
    )
    op.create_index(op.f('ix_book_author'), 'book', ['author'], unique=False)
    op.create_index(op.f('ix_book_id'), 'book', ['id'], unique=False)
    op.create_index(op.f('ix_book_isbn'), 'book', ['isbn'], unique=True)
    op.create_index(op.f('ix_book_title'), 'book', ['title'], unique=False)

    # Create table: member
    op.create_table('member',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_member_email'), 'member', ['email'], unique=True)
    op.create_index(op.f('ix_member_id'), 'member', ['id'], unique=False)
    op.create_index(op.f('ix_member_name'), 'member', ['name'], unique=False)

    # Create table: borrow_record
    op.create_table('borrow_record',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('member_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('borrowed_at', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('returned_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('borrowed', 'returned', name='borrowstatus'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['book_id'], ['book.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['member.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_borrow_record_id'), 'borrow_record', ['id'], unique=False)
    
    # Partial index for active borrows
    op.create_index('ix_active_borrows', 'borrow_record', ['book_id', 'member_id'], unique=False, postgresql_where=sa.text("status = 'borrowed'"))


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_active_borrows', table_name='borrow_record', postgresql_where=sa.text("status = 'borrowed'"))
    op.drop_index(op.f('ix_borrow_record_id'), table_name='borrow_record')
    op.drop_table('borrow_record')
    
    op.drop_index(op.f('ix_member_name'), table_name='member')
    op.drop_index(op.f('ix_member_id'), table_name='member')
    op.drop_index(op.f('ix_member_email'), table_name='member')
    op.drop_table('member')
    
    op.drop_index(op.f('ix_book_title'), table_name='book')
    op.drop_index(op.f('ix_book_isbn'), table_name='book')
    op.drop_index(op.f('ix_book_id'), table_name='book')
    op.drop_index(op.f('ix_book_author'), table_name='book')
    op.drop_table('book')

    # Drop ENUM type
    borrow_status_enum = postgresql.ENUM('borrowed', 'returned', name='borrowstatus')
    borrow_status_enum.drop(op.get_bind(), checkfirst=True)
