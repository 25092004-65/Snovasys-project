import hashlib, json
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from .models import AuditEvent

def log_event(db: Session, actor_id, action, document_id=None, detail="", success=True):
    last = db.scalar(select(AuditEvent).order_by(desc(AuditEvent.id)).limit(1))
    previous = last.event_hash if last else "0" * 64
    created = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    payload = {
        "actor_id": actor_id, "action": action, "document_id": document_id,
        "detail": detail[:1000], "success": success,
        "created_at": created.isoformat(), "previous_hash": previous
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    db.add(AuditEvent(
        actor_id=actor_id,
        action=action,
        document_id=document_id,
        detail=detail[:1000],
        success=success,
        created_at=created,
        previous_hash=previous,
        event_hash=digest
    ))
    db.commit()

def verify_audit_chain(db: Session):
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.id)).all()
    previous = "0" * 64
    for event in events:
        payload = {
            "actor_id": event.actor_id, "action": event.action, "document_id": event.document_id,
            "detail": event.detail, "success": event.success,
            "created_at": (event.created_at.replace(tzinfo=__import__("datetime").timezone.utc) if event.created_at.tzinfo is None else event.created_at).isoformat(), "previous_hash": previous
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        if event.previous_hash != previous or event.event_hash != digest:
            return False
        previous = event.event_hash
    return True
