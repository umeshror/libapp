from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def log_audit_event(
    session: Session,
    entity_type: str,
    entity_id: UUID,
    action: str,
    old_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    actor_id: Optional[str] = None,
) -> None:
    """
    Standardizes the creation of audit logs across the application.
    This should be called within the same transaction as the entity change.
    """
    # Filter out sensitive fields if necessary (e.g., in a real app)
    # For this POC, we'll store everything except the binary/internal fields
    
    audit_entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_state=old_state,
        new_state=new_state,
        actor_id=actor_id,
    )
    session.add(audit_entry)
    # Important: Do NOT commit here. Let the repository/service handle the transaction.
