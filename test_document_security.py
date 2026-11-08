def register(client, email, role_password="password123"):
    r = client.post("/auth/register", json={"email": email, "full_name": email.split("@")[0],
                                             "password": role_password})
    assert r.status_code == 200
    return r.json()["access_token"]

def test_viewer_cannot_upload(client):
    token = register(client, "viewer@example.com")
    r = client.post("/documents/upload", headers={"Authorization": f"Bearer {token}"},
                    files={"file": ("test.txt", b"hello", "text/plain")})
    assert r.status_code == 403

def test_private_document_not_visible_to_other_user(client):
    owner_token = register(client, "owner@example.com")
    viewer_token = register(client, "viewer@example.com")
    # Set owner role for this test only, simulating admin provisioning.
    from app.database import SessionLocal
    from app.models import User
    db = SessionLocal()
    owner = db.query(User).filter_by(email="owner@example.com").first()
    owner.role = "owner"; db.commit(); db.close()
    r = client.post("/documents/upload", headers={"Authorization": f"Bearer {owner_token}"},
                    files={"file": ("secret.txt", b"secret", "text/plain")})
    assert r.status_code == 200
    doc_id = r.json()["id"]
    denied = client.get(f"/documents/{doc_id}/download",
                        headers={"Authorization": f"Bearer {viewer_token}"})
    assert denied.status_code == 404

def test_revoke_access_blocks_next_download(client):
    owner_token = register(client, "owner2@example.com")
    viewer_token = register(client, "viewer2@example.com")
    from app.database import SessionLocal
    from app.models import User
    db = SessionLocal()
    owner = db.query(User).filter_by(email="owner2@example.com").first()
    owner.role = "owner"
    viewer = db.query(User).filter_by(email="viewer2@example.com").first()
    db.commit(); db.close()
    headers_owner = {"Authorization": f"Bearer {owner_token}"}
    headers_viewer = {"Authorization": f"Bearer {viewer_token}"}
    upload = client.post("/documents/upload", headers=headers_owner,
                         files={"file": ("note.txt", b"hello", "text/plain")})
    doc_id = upload.json()["id"]
    assert client.post(f"/documents/{doc_id}/permissions", headers=headers_owner,
                       json={"email": "viewer2@example.com", "permission": "read"}).status_code == 200
    assert client.get(f"/documents/{doc_id}/download", headers=headers_viewer).status_code == 200
    viewer_id = client.get("/auth/me", headers=headers_viewer).json()["id"]
    assert client.delete(f"/documents/{doc_id}/permissions/{viewer_id}",
                         headers=headers_owner).status_code == 200
    assert client.get(f"/documents/{doc_id}/download", headers=headers_viewer).status_code == 404
