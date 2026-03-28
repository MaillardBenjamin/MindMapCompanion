# Backend Personal Assistant - FastAPI avec JWT et PostgreSQL

Backend REST API développé avec FastAPI, incluant un système d'authentification JWT complet avec access tokens et refresh tokens, et une connexion à une base de données PostgreSQL.

## Fonctionnalités

- ✅ Authentification JWT intégrée (pas Auth0)
- ✅ Génération et gestion d'access tokens et refresh tokens
- ✅ Hachage sécurisé des mots de passe avec bcrypt
- ✅ Connexion PostgreSQL avec SQLAlchemy
- ✅ Migrations de base de données avec Alembic
- ✅ API REST pour l'authentification et la gestion des utilisateurs
- ✅ CORS configuré pour le frontend React

## Prérequis

- Python 3.9+
- PostgreSQL 12+
- pip (gestionnaire de paquets Python)

## Installation

1. **Cloner le projet et naviguer vers le répertoire backend**

```bash
cd backend
```

2. **Créer un environnement virtuel Python**

```bash
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. **Installer les dépendances**

```bash
pip install -r requirements.txt
```

4. **Configurer la base de données PostgreSQL**

Créez une base de données PostgreSQL :

```bash
createdb personal_assistant_db
```

Ou via psql :

```sql
CREATE DATABASE personal_assistant_db;
```

5. **Configurer les variables d'environnement**

Copiez le fichier `.env.example` vers `.env` :

```bash
cp .env.example .env
```

Éditez `.env` et configurez les variables :

```env
# Configuration de la base de données PostgreSQL
# Format: postgresql://username:password@host:port/database
# Note: Si le mot de passe contient des caractères spéciaux, ils doivent être encodés en URL:
# & devient %26, @ devient %40, : devient %3A, / devient %2F, etc.
DATABASE_URL=postgresql://user:password@localhost:5432/personal_assistant_db

# Configuration JWT
SECRET_KEY=votre-cle-secrete-tres-longue-et-aleatoire
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Configuration CORS
# Liste des origines autorisées (séparées par des virgules)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
CORS_ALLOW_CREDENTIALS=true
# Méthodes HTTP autorisées (séparées par des virgules, ou * pour toutes)
CORS_ALLOW_METHODS=*
# Headers autorisés (séparés par des virgules, ou * pour tous)
CORS_ALLOW_HEADERS=*
```

**Important** : 
- Changez `SECRET_KEY` par une clé secrète aléatoire et sécurisée en production
- Ajustez `CORS_ORIGINS` selon vos besoins (séparer plusieurs URLs par des virgules)

6. **Exécuter les migrations de base de données**

```bash
alembic upgrade head
```

## Démarrage du serveur

```bash
# Avec exclusion de venv pour éviter les reloads en boucle (WatchFiles ne surveille pas venv/)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude 'venv/*'

# Ou utiliser le script :
./run_dev.sh
```

Le serveur sera accessible sur `http://localhost:8000`

## Documentation de l'API

Une fois le serveur démarré, la documentation interactive est disponible :

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## Endpoints API

### Authentification

- `POST /api/auth/register` - Création d'un nouveau compte
  - Body: `{ "email": "user@example.com", "password": "password123" }`
  - Retourne: access_token, refresh_token

- `POST /api/auth/login` - Connexion
  - Body: `{ "email": "user@example.com", "password": "password123" }`
  - Retourne: access_token, refresh_token

- `POST /api/auth/refresh` - Renouvellement de l'access token
  - Body: `{ "refresh_token": "..." }`
  - Retourne: nouveau access_token

- `POST /api/auth/logout` - Déconnexion
  - Body: `{ "refresh_token": "..." }`
  - Invalide le refresh token

### Utilisateurs

- `GET /api/users/me` - Informations de l'utilisateur actuel
  - Headers: `Authorization: Bearer <access_token>`
  - Retourne: informations de l'utilisateur connecté

## Structure du projet

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Point d'entrée FastAPI
│   ├── config.py               # Configuration
│   ├── database.py             # Connexion PostgreSQL
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py             # Modèles SQLAlchemy
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py             # Schémas Pydantic
│   │   └── token.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py      # Gestion JWT
│   │   └── password.py         # Hachage mots de passe
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Dépendances FastAPI
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py         # Routes authentification
│   │       └── users.py        # Routes utilisateurs
│   └── crud/
│       ├── __init__.py
│       └── user.py             # Opérations CRUD
├── alembic/                    # Migrations
├── .env                        # Variables d'environnement (non versionné)
├── .env.example                # Exemple de configuration
├── requirements.txt            # Dépendances Python
├── alembic.ini                 # Configuration Alembic
└── README.md                   # Ce fichier
```

## Utilisation avec le frontend React

Le backend est configuré pour accepter les requêtes depuis :
- `http://localhost:3000` (Create React App)
- `http://localhost:5173` (Vite)

Pour ajouter d'autres origines, modifiez `app/main.py` :

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "votre-domaine.com"],
    ...
)
```

## Exemple d'utilisation

### Inscription

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

### Connexion

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

### Accès à une route protégée

```bash
curl -X GET "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer <access_token>"
```

### Refresh token

```bash
curl -X POST "http://localhost:8000/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

## Migrations de base de données

### Créer une nouvelle migration

```bash
alembic revision --autogenerate -m "Description de la migration"
```

### Appliquer les migrations

```bash
alembic upgrade head
```

### Revenir en arrière

```bash
alembic downgrade -1
```

## Sécurité

- Les mots de passe sont hachés avec bcrypt
- Les tokens JWT sont signés avec une clé secrète
- Les refresh tokens sont stockés en base de données et peuvent être invalidés
- Les routes protégées nécessitent un token valide dans le header Authorization

## Développement

Pour le développement avec rechargement automatique (sans surveiller `venv/`, pour éviter les redémarrages intempestifs) :

```bash
uvicorn app.main:app --reload --reload-exclude 'venv/*'
# ou
./run_dev.sh
```

## Production

Pour la production, utilisez un serveur ASGI comme Gunicorn avec Uvicorn workers :

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Support

Pour toute question ou problème, consultez la documentation FastAPI : https://fastapi.tiangolo.com/
