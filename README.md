# Personal Assistant

<div align="center">

![Personal Assistant](https://img.shields.io/badge/Personal-Assistant-blue?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-19-blue?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?style=for-the-badge&logo=fastapi)

**Une application complète de gestion de tâches et d'assistant personnel avec IA intégrée**

[Fonctionnalités](#-fonctionnalités) • [Installation](#-installation) • [Documentation](#-documentation) • [Contribuer](#-contribuer) • [Licence](#-licence)

</div>

---

## 📋 Table des matières

- [À propos](#-à-propos)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#️-architecture)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Documentation](#-documentation)
- [Tests](#-tests)
- [Contribuer](#-contribuer)
- [Sécurité](#-sécurité)
- [Projets liés](#-projets-liés)
- [Licence](#-licence)

## 🎯 À propos

Personal Assistant est une application web complète qui combine gestion de tâches, mindmaps interactifs, agents IA configurables et automatisation avancée. Conçue pour être votre assistant personnel intelligent, elle vous aide à organiser vos idées, planifier vos tâches et automatiser vos workflows.

### Points clés

- 🧠 **Agents IA configurables** - Créez et configurez vos propres agents IA pour automatiser vos tâches
- 📊 **Mindmaps interactifs** - Visualisez et organisez vos idées avec des mindmaps dynamiques
- ⚡ **Automatisation avancée** - Triggers, actions et planification (cron) pour automatiser vos workflows
- 📧 **Intégration email** - Réception et envoi d'emails automatiques
- 🔐 **Sécurité** - Authentification JWT complète avec refresh tokens
- 🎨 **Interface moderne** - UI/UX soignée avec React et Material-UI

## ✨ Fonctionnalités

### Gestion de tâches et mindmaps
- ✅ Création et gestion de nœuds (tâches, idées, projets)
- ✅ Mindmaps interactifs avec relations entre nœuds
- ✅ Système de statuts (inbox, ready, doing, waiting, done)
- ✅ Tags et métadonnées personnalisées
- ✅ Dates d'échéance avec rappels automatiques

### Agents IA
- ✅ Agents configurables avec Agno Framework
- ✅ Support de multiples modèles (OpenAI, Mistral, etc.)
- ✅ Schémas d'entrée personnalisables
- ✅ Exécution manuelle ou automatique via triggers

### Automatisation
- ✅ **Triggers** : Email reçu, Date atteinte, Cron, Changement d'état, Manuel
- ✅ **Actions** : Envoi d'email, Rappels, Mise à jour de nœuds, Appels API
- ✅ Planification avec expressions cron
- ✅ Actions de rappel personnalisables pour les échéances

### Email
- ✅ Réception automatique d'emails (IMAP)
- ✅ Envoi d'emails (SMTP)
- ✅ Création automatique de nœuds depuis les emails
- ✅ Templates d'emails personnalisables

### Recherche web
- ✅ Intégration avec Google Search et Bing
- ✅ Recherche web pour les agents IA
- ✅ MCP (Model Context Protocol) pour la recherche

## 🏗️ Architecture

### Stack technique

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web moderne et rapide
- [PostgreSQL](https://www.postgresql.org/) - Base de données relationnelle
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM Python
- [Alembic](https://alembic.sqlalchemy.org/) - Migrations de base de données
- [APScheduler](https://apscheduler.readthedocs.io/) - Planification de tâches
- [Agno Framework](https://github.com/agno-ai/agno) - Framework pour agents IA
- [JWT](https://jwt.io/) - Authentification sécurisée

**Frontend**
- [React](https://react.dev/) - Bibliothèque UI
- [TypeScript](https://www.typescriptlang.org/) - Typage statique
- [Vite](https://vitejs.dev/) - Build tool moderne
- [Material-UI](https://mui.com/) - Composants UI
- [React Flow](https://reactflow.dev/) - Graphiques interactifs
- [Zustand](https://github.com/pmndrs/zustand) - Gestion d'état

### Structure du projet

```
PersonalAssistant/
├── backend/              # API FastAPI
│   ├── app/             # Code de l'application
│   │   ├── agents/      # Agents IA
│   │   ├── api/         # Routes API
│   │   ├── models/      # Modèles SQLAlchemy
│   │   ├── schemas/     # Schémas Pydantic
│   │   ├── services/    # Services métier
│   │   └── routers/     # Routeurs FastAPI
│   ├── alembic/         # Migrations de base de données
│   └── tests/           # Tests unitaires
├── frontend/            # Interface React
│   └── src/
│       ├── components/  # Composants React
│       ├── features/    # Fonctionnalités
│       ├── stores/      # Gestion d'état
│       └── services/    # Services API
├── documentation/       # Documentation complète
├── shared/             # Types partagés
└── tests/              # Tests d'intégration
```

## 📦 Prérequis

- **Python** 3.9 ou supérieur
- **Node.js** 18 ou supérieur
- **PostgreSQL** 12 ou supérieur
- **Git**

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/MaillardBenjamin/MindMapCompanion.git
cd MindMapCompanion
```

### 2. Configuration du backend

```bash
cd backend

# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Sur Linux/Mac:
source venv/bin/activate
# Sur Windows:
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Configuration de la base de données

Créez une base de données PostgreSQL :

```bash
createdb personal_assistant
```

Ou via psql :

```sql
CREATE DATABASE personal_assistant;
```

### 4. Configuration des variables d'environnement

Créez un fichier `backend/.env` :

```env
# Base de données
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/personal_assistant

# JWT
JWT_SECRET_KEY=votre-cle-secrete-tres-longue-et-aleatoire
JWT_ALGORITHM=HS256
JWT_EXP_MINUTES=1440

# Authentification par défaut
AUTH_USERNAME=admin
AUTH_PASSWORD=admin

# Email (IMAP)
IMAP_HOST=mail.example.com
IMAP_PORT=993
IMAP_USER=your-email@example.com
IMAP_PASSWORD=your-password
IMAP_FOLDER=INBOX
IMAP_SSL=true
IMAP_POLL_MINUTES=2

# Agents IA
AGNO_MODEL=gpt-4
AGNO_API_KEY=your-agno-api-key
OPENAI_API_KEY=your-openai-api-key
MISTRAL_API_KEY=your-mistral-api-key

# Recherche web
GOOGLE_SEARCH_API_KEY=your-google-api-key
GOOGLE_SEARCH_ENGINE_ID=your-engine-id
BING_SEARCH_API_KEY=your-bing-api-key
SEARCH_PROVIDER=google

# CORS
CORS_ORIGINS=http://localhost:5173
```

### 5. Migrations de base de données

```bash
cd backend
alembic upgrade head
```

### 6. Configuration du frontend

```bash
cd frontend
npm install
```

## ⚙️ Configuration

### Variables d'environnement importantes

- `DATABASE_URL` : URL de connexion PostgreSQL
- `JWT_SECRET_KEY` : Clé secrète pour signer les tokens JWT (changez-la en production !)
- `IMAP_*` : Configuration pour la réception d'emails
- `*_API_KEY` : Clés API pour les services IA et de recherche

Consultez la [documentation complète](documentation/README.md) pour plus de détails.

## 🎮 Utilisation

### Démarrer le backend

```bash
cd backend
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Le serveur API sera accessible sur `http://localhost:8000`

### Démarrer le frontend

```bash
cd frontend
npm run dev
```

L'interface sera accessible sur `http://localhost:5173`

### Accès à l'application

- **Frontend** : http://localhost:5173
- **API Backend** : http://localhost:8000
- **Documentation API (Swagger)** : http://localhost:8000/docs
- **Documentation API (ReDoc)** : http://localhost:8000/redoc

### Compte par défaut

- **Username** : `admin`
- **Password** : `admin`

⚠️ **Important** : Changez ces identifiants en production !

## 📚 Documentation

### Documentation principale

- **[Index de la documentation](documentation/INDEX.md)** - Navigation complète
- **[Architecture technique](documentation/ARCHITECTURE.md)** - Vue technique détaillée
- **[Documentation fonctionnelle](documentation/FUNCTIONAL.md)** - Vue métier
- **[Documentation API](documentation/API.md)** - Référence complète des endpoints
- **[EPICS et User Stories](documentation/EPICS_USER_STORIES.md)** - Gestion produit

### Guides pratiques

- **[Guide de développement](documentation/DEVELOPMENT.md)** - Setup environnement de développement
- **[Guide de déploiement](documentation/DEPLOYMENT.md)** - Déploiement en production
- **[Guide de dépannage](documentation/TROUBLESHOOTING.md)** - Résolution de problèmes
- **[Guide de contribution](CONTRIBUTING.md)** - Comment contribuer au projet

## 🧪 Tests

### Tests backend

```bash
cd backend
pytest
```

### Tests frontend

```bash
cd frontend
npm test
```

### Tests d'intégration

```bash
# À la racine du projet
pytest tests/
```

## 🤝 Contribuer

Les contributions sont les bienvenues ! Veuillez lire notre [guide de contribution](CONTRIBUTING.md) pour plus de détails.

### Processus de contribution

1. Fork le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

### Code de conduite

Nous nous engageons à maintenir un environnement accueillant et respectueux. Veuillez consulter notre [Code de Conduite](CODE_OF_CONDUCT.md) (si disponible).

## 🔒 Sécurité

Si vous découvrez une vulnérabilité de sécurité, veuillez **ne pas** ouvrir une issue publique. Consultez notre [politique de sécurité](SECURITY.md) pour savoir comment signaler les vulnérabilités.

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

- [FastAPI](https://fastapi.tiangolo.com/) - Framework web incroyable
- [React](https://react.dev/) - Bibliothèque UI puissante
- [Material-UI](https://mui.com/) - Composants UI magnifiques
- [Agno Framework](https://github.com/agno-ai/agno) - Framework pour agents IA
- [MindMapCompanion](https://github.com/MaillardBenjamin/MindMapCompanion) - Projet inspirant pour les fonctionnalités de mindmap
- Tous les [contributeurs](https://github.com/MaillardBenjamin/MindMapCompanion/graphs/contributors) qui ont rendu ce projet possible

## 🔗 Projets liés

- [MindMapCompanion](https://github.com/MaillardBenjamin/MindMapCompanion) - Projet complémentaire pour la gestion de mindmaps avec IA

## 📞 Support

- 📖 [Documentation complète](documentation/INDEX.md)
- 🐛 [Signaler un bug](https://github.com/MaillardBenjamin/MindMapCompanion/issues)
- 💡 [Suggérer une fonctionnalité](https://github.com/MaillardBenjamin/MindMapCompanion/issues)
- 💬 [Discussions](https://github.com/MaillardBenjamin/MindMapCompanion/discussions)

## ⭐ Étoiles

Si ce projet vous est utile, n'hésitez pas à lui donner une étoile ⭐ !

---

<div align="center">

**Fait avec ❤️ par [Benjamin Maillard](https://github.com/MaillardBenjamin)**

[⬆ Retour en haut](#personal-assistant)

</div>
