Features
1. Three roles: Admin, Owner, Viewer.
2. Register and login.
3. Upload and manage documents.
4. Search documents.
5. Give and revoke access to named users.
6. Allow or reject document downloads based on permissions.
7. Record successful and denied access attempts.
8. Admin dashboard for audit activity.
9. Automated security tests.
10. THREATS.md, PROMPTS.md, API documentation and deployment.


2. Technology choices
Part	Technology
Frontend	React + Vite
Backend	Python + FastAPI
Database	PostgreSQL + SQLAlchemy
Authentication	JWT + password hashing
Testing	Pytest
Local file storage	Private backend folder
Deployment	Render + Vercel

For the first version, we'll store files in a private folder outside the frontend. For production, use persistent private storage; don't deploy uploaded files to an ephemeral filesystem.

Strucuture
TrustVault/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   ├── audit.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── documents.py
│   │       ├── permissions.py
│   │       └── admin.py
│   │
│   ├── tests/
│   │   ├── test_auth.py
│   │   └── test_document_security.py
│   ├── private_uploads/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── .env
│
├── THREATS.md
├── PROMPTS.md
└── README.md
