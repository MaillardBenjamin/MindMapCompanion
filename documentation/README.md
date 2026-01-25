# Documentation MVP

## Configuration backend
- Copier les variables d'environnement suivantes dans un fichier `backend/.env` :
  - `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/personal_assistant`
  - `JWT_SECRET_KEY=change-me`
  - `JWT_ALGORITHM=HS256`
  - `JWT_EXP_MINUTES=1440`
  - `AUTH_USERNAME=admin`
  - `AUTH_PASSWORD=admin`
  - `IMAP_HOST=imap.example.com`
  - `IMAP_PORT=993`
  - `IMAP_USER=user@example.com`
  - `IMAP_PASSWORD=app-password`
  - `IMAP_FOLDER=INBOX`
  - `IMAP_SSL=true`
  - `IMAP_POLL_MINUTES=2`
  - `AGNO_MODEL=gpt-4o-mini`
  - `AGNO_API_KEY=your-key`
  - `CORS_ORIGINS=http://localhost:5173`

## Lancement
- Backend : `python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt && alembic -c backend/alembic.ini upgrade head && uvicorn app.main:app --reload --app-dir backend`
- Frontend : `cd frontend && npm install && npm run dev`
