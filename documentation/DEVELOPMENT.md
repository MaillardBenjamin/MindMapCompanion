# Guide de Développement Local

Ce guide explique comment configurer un environnement de développement local pour Personal Assistant.

## 📋 Table des matières

- [Prérequis](#prérequis)
- [Configuration initiale](#configuration-initiale)
- [Développement Backend](#développement-backend)
- [Développement Frontend](#développement-frontend)
- [Tests](#tests)
- [Debugging](#debugging)
- [Outils recommandés](#outils-recommandés)

---

## 🔧 Prérequis

### Logiciels requis

- **Python** : 3.12+ ([Installation](https://www.python.org/downloads/))
- **Node.js** : 18+ ([Installation](https://nodejs.org/))
- **PostgreSQL** : 12+ ([Installation](https://www.postgresql.org/download/))
- **Git** : Pour le contrôle de version
- **Editor** : VS Code, PyCharm, ou équivalent

### Extensions recommandées (VS Code)

- **Python** : Microsoft
- **ESLint** : Microsoft
- **Prettier** : Prettier
- **GitLens** : GitKraken
- **Docker** : Microsoft (optionnel)

---

## 🚀 Configuration initiale

### 1. Cloner le repository

```bash
git clone https://github.com/your-org/personal-assistant.git
cd personal-assistant
```

### 2. Configuration Backend

```bash
cd backend

# Créer l'environnement virtuel
python3.12 -m venv venv

# Activer l'environnement
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Installer les dépendances de développement (si disponibles)
pip install pytest pytest-cov black isort flake8 mypy
```

### 3. Configuration Frontend

```bash
cd frontend

# Installer les dépendances
npm install

# Installer les dépendances de développement
npm install --save-dev @types/node @types/react
```

### 4. Configuration Base de données

```bash
# Créer la base de données locale
createdb personal_assistant

# Ou avec PostgreSQL
sudo -u postgres psql
CREATE DATABASE personal_assistant;
\q
```

### 5. Variables d'environnement

Créer `backend/.env` :

```env
# Base de données locale
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/personal_assistant

# JWT (développement)
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXP_MINUTES=1440

# Authentification (développement)
AUTH_USERNAME=admin
AUTH_PASSWORD=admin

# Email (optionnel pour dev local)
IMAP_HOST=mail.example.com
IMAP_PORT=993
IMAP_USER=dev@example.com
IMAP_PASSWORD=dev-password
IMAP_FOLDER=INBOX
IMAP_SSL=true
IMAP_POLL_MINUTES=2

# IA (nécessaire pour tester les agents)
AGNO_MODEL=gpt-4o-mini
AGNO_API_KEY=your-openai-api-key
OPENAI_API_KEY=your-openai-api-key

# CORS (développement)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Créer `frontend/.env.local` :

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 6. Migrations

```bash
cd backend
alembic upgrade head
```

---

## 💻 Développement Backend

### Structure du projet

```
backend/
├── app/
│   ├── api/routes/      # Routes API
│   ├── services/        # Logique métier
│   ├── models/          # Modèles SQLAlchemy
│   ├── schemas/         # Schémas Pydantic
│   ├── crud/            # Opérations CRUD
│   └── ...
├── tests/               # Tests
├── alembic/             # Migrations
└── requirements.txt     # Dépendances
```

### Lancer le serveur de développement

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Le serveur redémarre automatiquement lors des modifications (mode `--reload`).

### Créer une migration

```bash
# Après modification d'un modèle
alembic revision --autogenerate -m "description du changement"
alembic upgrade head
```

### Formatage du code

```bash
# Formatage automatique avec black
black backend/app/

# Tri des imports avec isort
isort backend/app/

# Vérification avec flake8
flake8 backend/app/
```

### Hot Reload

Le serveur redémarre automatiquement grâce à `--reload`. Pour un rechargement plus rapide :

```bash
# Utiliser watchfiles (plus rapide)
uvicorn app.main:app --reload --reload-engine watchfiles
```

---

## 🎨 Développement Frontend

### Structure du projet

```
frontend/
├── src/
│   ├── components/      # Composants React
│   ├── pages/           # Pages
│   ├── services/        # Services API
│   ├── stores/          # State management (Zustand)
│   └── ...
├── public/              # Assets statiques
└── package.json
```

### Lancer le serveur de développement

```bash
cd frontend
npm run dev
```

Le serveur démarre sur `http://localhost:5173` avec hot reload automatique.

### Build de production

```bash
npm run build
```

Les fichiers sont générés dans `frontend/dist/`.

### Formatage du code

```bash
# Linting
npm run lint

# Formatage avec Prettier
npm run format
```

---

## 🧪 Tests

### Tests Backend

```bash
cd backend
source venv/bin/activate

# Tous les tests
pytest

# Avec couverture
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_triggers.py

# Mode verbose
pytest -v

# Arrêter au premier échec
pytest -x
```

### Tests Frontend

```bash
cd frontend

# Lancer les tests
npm test

# Mode watch
npm test -- --watch

# Couverture
npm test -- --coverage
```

### Fixtures de test

Les fixtures sont dans `tests/conftest.py` :

```python
# Utilisation dans les tests
def test_create_node(db_session):
    node = create_node(db_session, ...)
    assert node.id is not None
```

---

## 🐛 Debugging

### Backend

**VS Code** : Créer `.vscode/launch.json` :

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": true
    }
  ]
}
```

**PyCharm** : Configuration Run/Debug pour uvicorn.

**Logs** :

```python
import logging
logger = logging.getLogger(__name__)
logger.debug("Message de debug")
logger.info("Message d'info")
logger.warning("Message d'avertissement")
logger.error("Message d'erreur")
```

### Frontend

**VS Code** : Utiliser Chrome Debugger extension.

**React DevTools** : Extension navigateur pour inspecter les composants.

**Console** : Utiliser `console.log()`, `console.error()`, etc.

**Breakpoints** : Dans DevTools > Sources.

---

## 🛠️ Outils recommandés

### Backend

- **Black** : Formatage automatique
- **isort** : Tri des imports
- **flake8** : Linting
- **mypy** : Vérification de types
- **pytest** : Framework de tests
- **ipdb** : Debugger interactif

### Frontend

- **ESLint** : Linting
- **Prettier** : Formatage
- **React DevTools** : Extension navigateur
- **Redux DevTools** : Pour Zustand (si utilisé)

### Base de données

- **pgAdmin** : Interface graphique PostgreSQL
- **DBeaver** : Client SQL universel
- **psql** : Client en ligne de commande

### API

- **Postman** : Test d'API
- **Insomnia** : Alternative à Postman
- **Swagger UI** : `http://localhost:8000/docs`

---

## 📝 Workflow de développement

### 1. Créer une branche

```bash
git checkout -b feature/ma-fonctionnalite
```

### 2. Développer

- Écrire le code
- Ajouter des tests
- Vérifier le formatage
- Tester localement

### 3. Commiter

```bash
git add .
git commit -m "feat: ajout de ma fonctionnalité"
```

### 4. Push et PR

```bash
git push origin feature/ma-fonctionnalite
# Créer une Pull Request sur GitHub
```

---

## 🔍 Vérifications avant commit

```bash
# Backend
black --check backend/app/
isort --check backend/app/
flake8 backend/app/
pytest backend/tests/

# Frontend
npm run lint
npm test
```

---

## 📚 Ressources

- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [Documentation React](https://react.dev/)
- [Documentation TypeScript](https://www.typescriptlang.org/)
- [Documentation PostgreSQL](https://www.postgresql.org/docs/)

---

**Bon développement ! 🚀**
