# Guide de Déploiement

Ce guide décrit comment déployer Personal Assistant en production.

## 📋 Table des matières

- [Prérequis](#prérequis)
- [Environnements](#environnements)
- [Déploiement Backend](#déploiement-backend)
- [Déploiement Frontend](#déploiement-frontend)
- [Base de données](#base-de-données)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Rollback](#rollback)

---

## 🔧 Prérequis

### Infrastructure

- **Serveur** : Linux (Ubuntu 20.04+ recommandé)
- **Python** : 3.12+
- **Node.js** : 18+
- **PostgreSQL** : 12+
- **Reverse Proxy** : Nginx ou équivalent
- **Process Manager** : systemd, PM2, ou Supervisor

### Services externes

- **OpenAI API** : Clé API pour les agents IA
- **Email** : Serveur SMTP/IMAP configuré
- **Domaine** : Nom de domaine avec DNS configuré

---

## 🌍 Environnements

### Développement

- **Backend** : `http://localhost:8000`
- **Frontend** : `http://localhost:5173`
- **Base de données** : PostgreSQL local

### Staging

- **Backend** : `https://api-staging.example.com`
- **Frontend** : `https://staging.example.com`
- **Base de données** : PostgreSQL dédié

### Production

- **Backend** : `https://api.example.com`
- **Frontend** : `https://example.com`
- **Base de données** : PostgreSQL avec réplication

---

## 🚀 Déploiement Backend

### 1. Préparation du serveur

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Installation de Python et dépendances
sudo apt install python3.12 python3.12-venv python3-pip postgresql postgresql-contrib

# Installation de Node.js (pour build frontend si nécessaire)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. Configuration PostgreSQL

```bash
# Créer l'utilisateur et la base de données
sudo -u postgres psql

CREATE USER personal_assistant WITH PASSWORD 'secure_password';
CREATE DATABASE personal_assistant OWNER personal_assistant;
GRANT ALL PRIVILEGES ON DATABASE personal_assistant TO personal_assistant;
\q
```

### 3. Déploiement de l'application

```bash
# Cloner le repository
git clone https://github.com/your-org/personal-assistant.git
cd personal-assistant/backend

# Créer l'environnement virtuel
python3.12 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Éditer .env avec les valeurs de production
nano .env

# Migrations
alembic upgrade head

# Tests
pytest tests/ -v
```

### 4. Configuration systemd

Créer `/etc/systemd/system/personal-assistant.service` :

```ini
[Unit]
Description=Personal Assistant API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/personal-assistant/backend
Environment="PATH=/opt/personal-assistant/backend/venv/bin"
ExecStart=/opt/personal-assistant/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activer le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable personal-assistant
sudo systemctl start personal-assistant
sudo systemctl status personal-assistant
```

### 5. Configuration Nginx

Créer `/etc/nginx/sites-available/personal-assistant-api` :

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activer et redémarrer :

```bash
sudo ln -s /etc/nginx/sites-available/personal-assistant-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. SSL avec Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com
```

---

## 🎨 Déploiement Frontend

### 1. Build de production

```bash
cd frontend
npm install
npm run build
```

Le build génère les fichiers dans `frontend/dist/`.

### 2. Configuration Nginx

Créer `/etc/nginx/sites-available/personal-assistant` :

```nginx
server {
    listen 80;
    server_name example.com;

    root /opt/personal-assistant/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activer :

```bash
sudo ln -s /etc/nginx/sites-available/personal-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. Variables d'environnement

Créer `frontend/.env.production` :

```env
VITE_API_BASE_URL=https://api.example.com
```

Rebuild après modification :

```bash
npm run build
```

---

## 🗄️ Base de données

### Sauvegarde

```bash
# Sauvegarde manuelle
pg_dump -U personal_assistant -h localhost personal_assistant > backup_$(date +%Y%m%d).sql

# Restauration
psql -U personal_assistant -h localhost personal_assistant < backup_20260122.sql
```

### Sauvegarde automatique (cron)

```bash
# Éditer crontab
crontab -e

# Ajouter (sauvegarde quotidienne à 2h du matin)
0 2 * * * pg_dump -U personal_assistant -h localhost personal_assistant > /backups/personal_assistant_$(date +\%Y\%m\%d).sql
```

### Migrations en production

```bash
# Vérifier l'état actuel
alembic current

# Appliquer les migrations
alembic upgrade head

# Rollback si nécessaire
alembic downgrade -1
```

---

## ⚙️ Configuration

### Variables d'environnement Backend

Fichier `.env` en production :

```env
# Base de données
DATABASE_URL=postgresql+asyncpg://personal_assistant:secure_password@localhost:5432/personal_assistant

# JWT
JWT_SECRET_KEY=<générer_une_clé_secrète_forte>
JWT_ALGORITHM=HS256
JWT_EXP_MINUTES=1440

# Authentification
AUTH_USERNAME=admin
AUTH_PASSWORD=<mot_de_passe_fort_hashé>

# Email IMAP
IMAP_HOST=mail.example.com
IMAP_PORT=993
IMAP_USER=contact@example.com
IMAP_PASSWORD=<app_password>
IMAP_FOLDER=INBOX
IMAP_SSL=true
IMAP_POLL_MINUTES=2

# Email SMTP
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=contact@example.com
SMTP_PASSWORD=<app_password>
SMTP_USE_TLS=true

# IA
AGNO_MODEL=gpt-4o-mini
AGNO_API_KEY=<openai_api_key>
OPENAI_API_KEY=<openai_api_key>

# CORS
CORS_ORIGINS=https://example.com,https://www.example.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=*

# Environnement
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Sécurité

- **Ne jamais commiter** le fichier `.env`
- Utiliser des secrets managers (HashiCorp Vault, AWS Secrets Manager)
- Rotation régulière des clés API
- Mots de passe forts (min. 16 caractères)

---

## 📊 Monitoring

### Logs

```bash
# Logs système
sudo journalctl -u personal-assistant -f

# Logs Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Logs application
tail -f /opt/personal-assistant/backend/logs/app.log
```

### Health Checks

Endpoint de santé : `GET /health`

```bash
curl https://api.example.com/health
```

### Métriques

- **Uptime** : Monitoring avec UptimeRobot ou Pingdom
- **Performance** : APM avec New Relic ou Datadog
- **Erreurs** : Sentry pour le tracking d'erreurs

---

## 🔄 Rollback

### Rollback Backend

```bash
# Arrêter le service
sudo systemctl stop personal-assistant

# Checkout version précédente
cd /opt/personal-assistant/backend
git checkout <previous-tag>

# Rollback migrations si nécessaire
alembic downgrade -1

# Redémarrer
sudo systemctl start personal-assistant
```

### Rollback Frontend

```bash
# Checkout version précédente
cd /opt/personal-assistant/frontend
git checkout <previous-tag>

# Rebuild
npm run build

# Redémarrer Nginx
sudo systemctl restart nginx
```

---

## 🐳 Déploiement Docker (Optionnel)

### Dockerfile Backend

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/personal_assistant
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  db:
    image: postgres:12
    environment:
      POSTGRES_DB: personal_assistant
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## ✅ Checklist de déploiement

- [ ] Serveur configuré et sécurisé
- [ ] Base de données créée et migrée
- [ ] Variables d'environnement configurées
- [ ] SSL/TLS configuré
- [ ] Backend déployé et testé
- [ ] Frontend buildé et déployé
- [ ] Monitoring configuré
- [ ] Sauvegardes automatiques configurées
- [ ] Documentation mise à jour
- [ ] Tests de charge effectués

---

**Note** : Ce guide est un template. Adaptez-le selon votre infrastructure et besoins spécifiques.
