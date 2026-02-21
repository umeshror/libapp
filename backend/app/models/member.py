import uuid
from sqlalchemy import Column, String, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin


class Member(Base, TimestampMixin):
    """
    Core domain model representing library patrons.
    Email addresses must be unique across all members.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_member_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
        Index("ix_member_email_trgm", "email", postgresql_using="gin", postgresql_ops={"email": "gin_trgm_ops"}),
    )
