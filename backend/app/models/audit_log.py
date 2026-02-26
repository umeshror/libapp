import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, JSON, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class AuditLog(Base):
    """
    Tracks all administrative and lifecycle changes to core entities.
    Stores pre and post-change snapshots as JSON for historic auditing.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    entity_type = Column(String, index=True, nullable=False)  # e.g., 'book', 'member'
    entity_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    action = Column(String, index=True, nullable=False)  # e.g., 'create', 'update', 'delete', 'restore'
    
    # Store changes as snapshots
    old_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    
    # Metadata
    actor_id = Column(String, nullable=True)  # For future auth integration
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_audit_log_entity_composite", "entity_type", "entity_id"),
    )
