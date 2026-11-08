from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from ..database import get_db
from ..models import AuditEvent, User
from ..dependencies import require_admin
from ..audit import verify_audit_chain

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/audit")
def audit_events(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditEvent).order_by(desc(AuditEvent.id)).limit(500)).all()
    return [{"id": x.id, "actor_id": x.actor_id, "action": x.action,
             "document_id": x.document_id, "detail": x.detail,
             "success": x.success, "created_at": x.created_at} for x in rows]

@router.get("/audit/verify")
def audit_verify(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return {"valid": verify_audit_chain(db)}
