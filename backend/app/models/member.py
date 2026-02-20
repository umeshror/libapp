import uuid
from sqlalchemy import Column, String
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
