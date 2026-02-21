"""add_pg_trgm_search_indexes

Revision ID: 8d8bbb389bc4
Revises: 74244ea76416
Create Date: 2026-02-20 16:18:33.369984

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d8bbb389bc4'
down_revision = '74244ea76416'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        op.execute("CREATE INDEX IF NOT EXISTS ix_book_title_trgm ON book USING GIN (title gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_book_author_trgm ON book USING GIN (author gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_book_isbn_trgm ON book USING GIN (isbn gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_member_name_trgm ON member USING GIN (name gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_member_email_trgm ON member USING GIN (email gin_trgm_ops);")

def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP INDEX IF EXISTS ix_member_email_trgm;")
        op.execute("DROP INDEX IF EXISTS ix_member_name_trgm;")
        op.execute("DROP INDEX IF EXISTS ix_book_isbn_trgm;")
        op.execute("DROP INDEX IF EXISTS ix_book_author_trgm;")
        op.execute("DROP INDEX IF EXISTS ix_book_title_trgm;")
        op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
