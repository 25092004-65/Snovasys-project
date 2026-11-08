from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routers import auth, documents, permissions, admin

Base.metadata.create_all(bind=engine)
app = FastAPI(title="TrustVault API", version="1.0.0",
              description="Secure document sharing with role-based access and an audit trail.")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173",],allow_credentials=True,allow_methods=["*"],allow_headers=["*"],)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(permissions.router)
app.include_router(admin.router)

@app.get("/")
def health():
    return {"message": "TrustVault API is running", "docs": "/docs"}
