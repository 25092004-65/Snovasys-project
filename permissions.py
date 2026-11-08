from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..models import User, Document, DocumentPermission
from ..schemas import PermissionIn
from ..dependencies import current_user
from ..audit import log_event

router = APIRouter(prefix="/documents", tags=["Permissions"])

def owned_doc(db, document_id, user):
    doc = db.get(Document, document_id)
    if not doc or doc.owner_id != user.id:
        raise HTTPException(404, "Document not found")
    return doc

@router.post("/{document_id}/permissions")
def grant_access(document_id: int, data: PermissionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = owned_doc(db, document_id, user)
    if data.permission not in ("read", "write"):
        raise HTTPException(400, "Permission must be read or write")
    target = db.scalar(select(User).where(User.email == data.email.lower()))
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == user.id:
        raise HTTPException(400, "You already own this document")
    row = db.scalar(select(DocumentPermission).where(
        DocumentPermission.document_id == doc.id, DocumentPermission.user_id == target.id))
    if row:
        row.permission = data.permission
        row.granted_by = user.id
    else:
        db.add(DocumentPermission(document_id=doc.id, user_id=target.id,
                                  permission=data.permission, granted_by=user.id))
    db.commit()
    log_event(db, user.id, "ACCESS_GRANTED", doc.id, f"{data.permission} access granted to user {target.id}")
    return {"message": "Access granted"}

@router.delete("/{document_id}/permissions/{target_user_id}")
def revoke_access(document_id: int, target_user_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = owned_doc(db, document_id, user)
    row = db.scalar(select(DocumentPermission).where(
        DocumentPermission.document_id == doc.id, DocumentPermission.user_id == target_user_id))
    if not row:
        raise HTTPException(404, "Permission not found")
    db.delete(row); db.commit()
    log_event(db, user.id, "ACCESS_REVOKED", doc.id, f"Access revoked from user {target_user_id}")
    return {"message": "Access revoked immediately"}
