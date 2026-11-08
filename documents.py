import os, uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from ..database import get_db
from ..models import User, Document, DocumentPermission
from ..dependencies import current_user
from ..audit import log_event

router = APIRouter(prefix="/documents", tags=["Documents"])
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./private_uploads")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
ALLOWED = {".pdf": {"application/pdf"}, ".txt": {"text/plain"},
           ".png": {"image/png"}, ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"}}

def can_read(db, doc, user):
    if doc.owner_id == user.id:
        return True
    return db.scalar(select(DocumentPermission).where(
        DocumentPermission.document_id == doc.id,
        DocumentPermission.user_id == user.id,
        DocumentPermission.permission.in_(["read", "write"])
    )) is not None

def get_doc(db, doc_id):
    return db.get(Document, doc_id)

@router.post("/upload")
async def upload(file: UploadFile = File(...), category: str = Form("General"),
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role not in ("owner", "admin"):
        log_event(db, user.id, "UPLOAD_DENIED", detail="Role cannot upload", success=False)
        raise HTTPException(403, "Only document owners can upload")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED or file.content_type not in ALLOWED[suffix]:
        log_event(db, user.id, "UPLOAD_REJECTED", detail="Unsupported extension or MIME type", success=False)
        raise HTTPException(400, "Allowed file types: PDF, TXT, PNG, JPG")
    content = await file.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(400, f"File must be between 1 byte and {MAX_BYTES // (1024*1024)} MB")
    stored = uuid.uuid4().hex
    path = UPLOAD_DIR / stored
    path.write_bytes(content)
    doc = Document(owner_id=user.id, original_name=Path(file.filename).name[:255],
                   stored_name=stored, content_type=file.content_type,
                   size_bytes=len(content), category=category[:80])
    db.add(doc); db.commit(); db.refresh(doc)
    log_event(db, user.id, "UPLOAD", doc.id, f"Uploaded {doc.original_name}")
    return {"id": doc.id, "name": doc.original_name, "category": doc.category}

@router.get("")
def list_documents(q: str = Query("", max_length=100), category: str = "",
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    docs = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    visible = []
    for doc in docs:
        if can_read(db, doc, user) and (not q or q.lower() in doc.original_name.lower()) and (not category or category.lower() in doc.category.lower()):
            visible.append({"id": doc.id, "name": doc.original_name, "owner_id": doc.owner_id,
                            "category": doc.category, "size_bytes": doc.size_bytes,
                            "created_at": doc.created_at})
    log_event(db, user.id, "DOCUMENT_LIST", detail=f"Returned {len(visible)} visible documents")
    return visible

@router.get("/{document_id}/download")
def download(document_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = get_doc(db, document_id)
    if not doc or not can_read(db, doc, user):
        log_event(db, user.id, "DOWNLOAD_DENIED", document_id, "Document missing or user has no permission", False)
        raise HTTPException(404, "Document not found")  # avoid revealing whether it exists
    path = UPLOAD_DIR / doc.stored_name
    if not path.is_file():
        log_event(db, user.id, "DOWNLOAD_FAILED", document_id, "Stored file missing", False)
        raise HTTPException(404, "Document file not found")
    log_event(db, user.id, "DOWNLOAD", document_id, f"Downloaded {doc.original_name}")
    return FileResponse(path, filename=doc.original_name, media_type=doc.content_type)

@router.delete("/{document_id}")
def delete_document(document_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = get_doc(db, document_id)
    if not doc or doc.owner_id != user.id:
        log_event(db, user.id, "DELETE_DENIED", document_id, "Only owner may delete", False)
        raise HTTPException(404, "Document not found")
    path = UPLOAD_DIR / doc.stored_name
    if path.exists(): path.unlink()
    db.query(DocumentPermission).filter_by(document_id=doc.id).delete()
    db.delete(doc); db.commit()
    log_event(db, user.id, "DELETE", document_id, "Owner deleted document")
    return {"message": "Document deleted"}
