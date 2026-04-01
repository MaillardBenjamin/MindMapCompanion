# Documentation d'Architecture Technique (DAT)

## Vue d'ensemble

**Personal Assistant** est une application web complète de gestion de tâches et d'assistant personnel intelligent, basée sur une architecture client-serveur moderne avec séparation claire des responsabilités.

### Stack technologique

- **Backend** : FastAPI (Python 3.12+)
- **Frontend** : React 19 + TypeScript + Vite
- **Base de données** : PostgreSQL avec SQLAlchemy (ORM)
- **Authentification** : JWT (JSON Web Tokens)
- **Scheduling** : APScheduler (tâches planifiées)
- **IA** : Agno Framework + OpenAI API
- **Email** : IMAP (réception) + SMTP (envoi)

---

## Architecture générale

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Dashboard  │  │   Mindmap    │  │   Agents    │      │
│  │   Component  │  │   Canvas     │  │   List      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            │                                │
│                    ┌───────▼────────┐                       │
│                    │  API Client    │                       │
│                    │  (services/)   │                       │
│                    └───────┬────────┘                       │
└────────────────────────────┼─────────────────────────────────┘
                             │ HTTP/REST
                             │ JWT Auth
┌────────────────────────────▼─────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Routes (app/api/routes/)             │   │
│  │  auth │ users │ mindmaps │ nodes │ triggers │ actions │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                 │
│  ┌─────────────────────────┼─────────────────────────────┐   │
│  │  Services Layer         │  Routers (app/routers/)     │   │
│  │  - Agent Service       │  - Agents                   │   │
│  │  - Scheduler           │  - Configurable Agents      │   │
│  │  - Email (IMAP/SMTP)   │  - Admin                    │   │
│  │  - Web Search          │  - Ingest                   │   │
│  └─────────────────────────┼─────────────────────────────┘   │
│                            │                                 │
│  ┌─────────────────────────┼─────────────────────────────┐   │
│  │  CRUD Layer             │  Models (SQLAlchemy)       │   │
│  │  - User CRUD            │  - User, Node, Trigger      │   │
│  │  - Mindmap CRUD         │  - Action, Edge, Proposal   │   │
│  │  - Agent CRUD            │  - ConfigurableAgent        │   │
│  └─────────────────────────┼─────────────────────────────┘   │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │   PostgreSQL   │                        │
│                    │   (AsyncPG)   │                        │
│                    └────────────────┘                        │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         Background Services (APScheduler)            │    │
│  │  - Poll IMAP (toutes les 2 min)                     │    │
│  │  - Run due triggers (toutes les 1 min)              │    │
│  │  - Cron triggers (selon expression)                 │    │
│  │  - Reload cron triggers (toutes les 5 min)          │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

---

## Structure du backend

### Organisation des modules

```
backend/app/
├── main.py                    # Point d'entrée FastAPI
├── config.py                   # Configuration (CORS, JWT)
├── core/
│   ├── config.py              # Settings (DB, IMAP, AI)
│   ├── deps.py                # Dépendances FastAPI
│   └── security.py            # Sécurité (hashing)
├── api/
│   └── routes/                # Routes API principales
│       ├── auth.py            # Authentification JWT
│       ├── users.py           # Gestion utilisateurs
│       ├── mindmaps.py        # Mindmaps
│       ├── nodes.py           # Nœuds du mindmap
│       ├── triggers.py        # Triggers (déclencheurs)
│       └── actions.py         # Actions automatisées
├── routers/                   # Routers additionnels
│   ├── agents.py             # Agents IA
│   ├── configurable_agents.py # Agents configurables
│   ├── admin.py              # Administration
│   └── ingest.py             # Ingestion de texte
├── models/                    # Modèles SQLAlchemy
│   ├── user.py               # Utilisateur
│   ├── node.py               # Nœud (idée, tâche, etc.)
│   ├── trigger.py            # Déclencheur
│   ├── action.py             # Action
│   ├── configurable_agent.py # Agent configurable
│   └── ...
├── schemas/                   # Schémas Pydantic (validation)
│   ├── auth.py
│   ├── node.py
│   ├── trigger.py
│   └── ...
├── crud/                      # Opérations CRUD
│   ├── user.py
│   ├── mindmap.py
│   └── configurable_agent.py
├── services/                  # Logique métier
│   ├── configurable_agent_service.py  # Exécution agents
│   ├── scheduler.py                   # Planification
│   ├── email_imap.py                  # Réception email
│   ├── email_smtp.py                  # Envoi email
│   ├── web_search.py                  # Recherche web
│   ├── agent_structurer.py           # Structuration IA
│   └── ...
├── tools/                     # Outils pour agents
│   └── web_search_tools.py    # Outils de recherche web
├── mcp/                       # Model Context Protocol
│   └── web_search_server.py   # Serveur MCP recherche
└── db/
    └── session.py             # Sessions async PostgreSQL
```

### Patterns architecturaux

#### 1. **Séparation des couches (Layered Architecture)**

- **Couche API** : Routes FastAPI (`api/routes/`, `routers/`)
- **Couche Service** : Logique métier (`services/`)
- **Couche CRUD** : Accès données (`crud/`)
- **Couche Modèle** : Entités de données (`models/`)

#### 2. **Dependency Injection**

FastAPI utilise le système de dépendances pour :
- Authentification (`get_current_user`)
- Sessions DB (`get_db`, `get_async_session`)
- Configuration (`get_settings`)

#### 3. **Repository Pattern**

Les opérations CRUD sont centralisées dans `crud/` pour :
- Isolation de la logique d'accès données
- Réutilisabilité
- Testabilité

#### 4. **Service Layer Pattern**

La logique métier complexe est dans `services/` :
- `ConfigurableAgentService` : Exécution d'agents IA
- `Scheduler` : Planification de tâches
- `EmailService` : Gestion email

---

## Base de données

### Schéma principal

```sql
-- Utilisateurs
users (id, email, hashed_password, is_active, ...)

-- Mindmaps (conceptuel, non implémenté en DB)
-- Les nœuds sont directement liés aux utilisateurs via source_ref

-- Nœuds (éléments du mindmap)
nodes (
  id (UUID),
  raw_text,
  title,
  type (idea|task|note|project|event),
  status (inbox|clarify|ready|doing|waiting|done),
  source (ui|email|api),
  tags (JSONB),
  position (JSONB),
  ai_meta (JSONB),
  ...
)

-- Relations entre nœuds
edges (
  id (UUID),
  from_node_id,
  to_node_id,
  relation_type (related|parent|depends_on|mentions|reference),
  confidence,
  created_by (human|ai)
)

-- Triggers (déclencheurs)
triggers (
  id (UUID),
  node_id,
  trigger_type (email_received|date_reached|cron|state_changed|manual),
  config (JSONB),
  enabled,
  last_fired_at,
  dedupe_key
)

-- Actions (actions automatisées)
actions (
  id,
  trigger_id,
  type (send_email|draft_email|call_api|update_node|run_agent|...),
  order,
  enabled,
  config (JSONB)
)

-- Agents configurables
configurable_agents (
  id,
  user_id,
  name,
  slug,
  prompt_template,
  output_schema (JSON),
  tools (JSON),
  persona,
  instructions,
  ...
)

-- Logs d'exécution
agent_execution_logs (
  id,
  agent_id,
  user_id,
  input_text,
  output_raw,
  output_parsed (JSON),
  execution_time_ms,
  ...
)
```

### Migrations

Utilisation d'**Alembic** pour les migrations :
- Fichiers dans `alembic/versions/`
- Commande : `alembic upgrade head`

---

## Authentification et sécurité

### JWT (JSON Web Tokens)

**Flux d'authentification** :
1. Login → `/api/auth/token` (username/password)
2. Backend vérifie credentials
3. Génère `access_token` (courte durée) + `refresh_token` (longue durée)
4. Frontend stocke les tokens dans `localStorage`
5. Chaque requête inclut `Authorization: Bearer <access_token>`

**Refresh Token** :
- Si `access_token` expire (401), frontend utilise `refresh_token`
- Backend génère un nouveau `access_token`
- Rotation automatique des tokens

**Sécurité** :
- Mots de passe hashés avec `bcrypt`
- Tokens signés avec `HS256`
- CORS configuré pour limiter les origines

---

## Services backend

### 1. ConfigurableAgentService

**Responsabilité** : Exécuter des agents IA configurables

**Fonctionnalités** :
- Parse la configuration Markdown de l'agent
- Crée un agent Agno avec le modèle OpenAI
- Configure les outils (web_search, etc.)
- Exécute l'agent avec un input_text
- Parse la sortie Markdown selon le schéma attendu
- Log l'exécution dans `agent_execution_logs`

**Flux d'exécution** :
```
Input Text → Agent Agno → LLM (OpenAI) → Markdown Output
                ↓
         Tools (web_search, etc.)
                ↓
         Parsed Output (JSON)
```

### 2. Scheduler (APScheduler)

**Responsabilité** : Planifier et exécuter des tâches automatiques

**Jobs configurés** :
- `poll_imap` : Toutes les 2 minutes
  - Récupère les emails non lus
  - Crée des nœuds dans l'inbox
  - Génère des propositions de structuration

- `run_due_triggers` : Toutes les 1 minute
  - Exécute les triggers `date_reached` échus

- `cron_trigger_{id}` : Selon expression cron
  - Exécute les triggers `cron` planifiés

- `reload_cron_triggers` : Toutes les 5 minutes
  - Recharge les triggers cron depuis la DB

**Exécution de trigger** :
```python
execute_trigger_with_config(trigger)
  → Lit config (task_type, task_id, output_type)
  → Si agent: exécute ConfigurableAgentService
  → Si action: exécute execute_actions_for_node
  → Si output_type=email: envoie par SMTP
```

### 3. Email Services

**IMAP (Réception)** :
- Connexion SSL au serveur IMAP
- Polling périodique (toutes les 2 min)
- Extraction des emails non lus
- Création automatique de nœuds

**SMTP (Envoi)** :
- Envoi d'emails multipart (text + HTML)
- Formatage Markdown → HTML
- Support des résultats d'agents

### 4. Web Search Service

**Fournisseurs supportés** :
- Google Custom Search API (via SerpAPI)
- Bing Search API

**Fonctionnalités** :
- Recherche web générale
- Recherche d'actualités
- Mock search pour tests (sans API)

**Intégration** :
- Outils disponibles pour agents IA
- Serveur MCP pour protocole standardisé

---

## Structure du frontend

### Organisation

```
frontend/src/
├── App.tsx                    # Point d'entrée React
├── main.tsx                   # Bootstrap React
├── pages/                     # Pages principales
│   ├── Landing.tsx           # Page d'accueil
│   ├── Login.tsx             # Connexion
│   └── Dashboard.tsx         # Tableau de bord
├── components/               # Composants réutilisables
│   ├── Layout/               # Layout (Header, Footer)
│   ├── Mindmap/              # Composants mindmap
│   │   ├── MindmapCanvas.tsx
│   │   ├── NodeDetails.tsx
│   │   └── ...
│   ├── Trigger/              # Configuration triggers
│   └── Agents/               # Liste agents
├── stores/                   # State management (Zustand)
│   ├── authStore.ts          # État authentification
│   └── mindmapStore.ts      # État mindmap
├── services/                 # Services API
│   └── api.ts               # Client API avec auth
├── config/                   # Configuration
│   └── api.ts               # Endpoints API
└── theme/                    # Thème Material-UI
    └── theme.ts
```

### State Management

**Zustand** pour la gestion d'état :
- `authStore` : Tokens, utilisateur connecté
- `mindmapStore` : Nœuds, sélection, édition

**Avantages** :
- Léger et simple
- Pas de boilerplate (vs Redux)
- TypeScript natif

### Routing

**React Router v6** :
- Routes publiques : `/`, `/login`
- Routes protégées : `/dashboard`
- Redirection automatique selon auth

### UI Framework

**Material-UI (MUI)** :
- Composants Material Design
- Thème personnalisé (dark mode)
- Responsive design

---

## Communication Frontend ↔ Backend

### API REST

**Endpoints principaux** :

```
POST   /api/auth/token              # Login
POST   /api/auth/refresh            # Refresh token
GET    /api/users/me                # Utilisateur courant

GET    /api/mindmaps                # Liste mindmaps
GET    /api/nodes                   # Liste nœuds
POST   /api/nodes                   # Créer nœud
PATCH  /api/nodes/{id}              # Modifier nœud

GET    /api/triggers/node/{id}      # Triggers d'un nœud
POST   /api/triggers                # Créer trigger
PUT    /api/triggers/{id}           # Modifier trigger
POST   /api/triggers/{id}/execute   # Exécuter trigger

GET    /api/configurable-agents     # Liste agents
POST   /api/configurable-agents/{id}/execute  # Exécuter agent
```

### Authentification

**Headers requis** :
```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Gestion des tokens** :
- Stockage : `localStorage`
- Refresh automatique en cas d'expiration
- Intercepteurs axios pour injection du token

---

## Agents IA configurables

### Architecture

**Agno Framework** :
- Framework Python pour agents IA
- Support de multiples modèles (OpenAI, etc.)
- Système d'outils extensible

**Configuration Markdown** :
- Format YAML frontmatter + Markdown
- Définition du persona, instructions, schéma de sortie
- Outils disponibles (web_search, etc.)

**Exécution** :
1. Parse la config Markdown
2. Crée l'agent Agno avec le modèle OpenAI
3. Configure les outils demandés
4. Exécute avec `input_text`
5. Parse la sortie Markdown selon le schéma
6. Retourne `output_raw` (Markdown) + `output_parsed` (JSON)

### Outils disponibles

- `web_search` : Recherche web générale
- `web_search_news` : Recherche d'actualités
- Extensible via MCP (Model Context Protocol)

---

## Planification et automatisation

### Types de triggers

1. **`email_received`** : Déclenché à la réception d'un email
2. **`date_reached`** : Déclenché à une date/heure précise
3. **`cron`** : Déclenché selon expression cron (ex: `0 9 * * 1,3,5`)
4. **`state_changed`** : Déclenché au changement d'état d'un nœud
5. **`manual`** : Déclenché manuellement par l'utilisateur

### Actions disponibles

- `send_email` : Envoyer un email
- `draft_email` : Rédiger un email (brouillon)
- `call_api` : Appeler une API externe
- `update_node` : Modifier un nœud
- `run_agent` : Exécuter un agent IA
- `notify` : Notification
- `create_reminder` : Créer un rappel

### Flux d'exécution

```
Trigger déclenché
    ↓
Lecture de config (task_type, task_id, output_type)
    ↓
┌─────────────┬─────────────┐
│  task_type  │  task_type  │
│  = "agent"  │  = "action"  │
└──────┬──────┴──────┬───────┘
       │            │
   Exécute      Exécute
   Agent IA     Actions
       │            │
       └──────┬─────┘
              ↓
    ┌─────────────────┐
    │  output_type ?  │
    └────┬──────┬──────┘
         │      │
    "screen"  "email"
         │      │
    Affiche   Envoie
    résultat  par SMTP
```

---

## Gestion des emails

### Réception (IMAP)

**Flux** :
1. Scheduler appelle `poll_imap()` toutes les 2 min
2. Connexion IMAP SSL au serveur
3. Recherche des emails non lus (`UNSEEN`)
4. Pour chaque email :
   - Création d'un nœud dans l'inbox
   - Source : `NodeSource.email`
   - Génération d'une proposition de structuration IA
   - Marquage comme traité

**Déduplication** :
- Utilisation de `idempotency_key` basé sur `Message-ID`
- Évite les doublons en cas de re-polling

### Envoi (SMTP)

**Flux** :
1. Formatage du contenu (Markdown → HTML)
2. Création d'un email multipart (text + HTML)
3. Envoi via SMTP
4. Logging détaillé

**Cas d'usage** :
- Résultats d'agents IA
- Notifications
- Rappels

---

## Recherche web

### Architecture

**Service centralisé** : `WebSearchService`
- Support Google (SerpAPI) et Bing
- Recherche générale et actualités
- Fallback sur mock search si API non configurée

**Intégration agents** :
- Outils disponibles pour agents IA
- Format standardisé (`WebSearchResult`)
- Conversion automatique en dictionnaires

**MCP Server** :
- Protocole standardisé pour agents
- Endpoints REST pour recherche
- Compatible avec frameworks d'agents

---

## Logging et monitoring

### Logging structuré

**Niveaux** :
- `INFO` : Opérations normales
- `WARNING` : Situations anormales non bloquantes
- `ERROR` : Erreurs nécessitant attention

**Format** :
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**Logs importants** :
- Exécution d'agents (temps, succès/échec)
- Exécution de triggers
- Envoi d'emails
- Erreurs de connexion DB/IMAP

---

## Déploiement

### Prérequis

- Python 3.12+
- Node.js 18+
- PostgreSQL 12+
- Variables d'environnement configurées

### Variables d'environnement

**Backend** (`backend/.env`) :
```env
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET_KEY=...
AGNO_API_KEY=...
OPENAI_API_KEY=...
IMAP_HOST=...
IMAP_USER=...
IMAP_PASSWORD=...
CORS_ORIGINS=http://localhost:5173,...
```

**Frontend** :
- `VITE_API_BASE_URL` : URL du backend (défaut: http://localhost:8000)

### Processus de démarrage

1. **Backend** :
   ```bash
   cd backend
   source venv/bin/activate
   alembic upgrade head  # Migrations DB
   uvicorn app.main:app --reload
   ```

2. **Frontend** :
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Sécurité

### Authentification

- JWT avec expiration courte (access_token)
- Refresh tokens avec rotation
- Hashing bcrypt pour mots de passe

### CORS

- Origines autorisées configurées
- Credentials activés
- Headers personnalisés

### Validation

- Pydantic pour validation des données
- Schémas stricts pour API
- Sanitization des inputs

---

## Extensibilité

### Ajout d'un nouvel agent

1. Créer un fichier `.md` dans `app/agent_configs/agents/`
2. Format YAML frontmatter + Markdown
3. Définir persona, instructions, schéma de sortie
4. Charger via endpoint `/admin/load-agents-from-files`

### Ajout d'un nouvel outil

1. Créer fonction dans `app/tools/`
2. Ajouter à `get_web_search_tools()` ou créer nouveau module
3. Référencer dans config agent (`tools: ["nouvel_outil"]`)

### Ajout d'un nouveau type de trigger

1. Ajouter valeur à `TriggerType` enum
2. Implémenter logique dans `scheduler.py`
3. Ajouter UI dans `TriggerForm.tsx`

---

## Performance

### Optimisations

- **Async/await** : Opérations I/O asynchrones
- **Connection pooling** : PostgreSQL avec asyncpg
- **Lazy loading** : Relations SQLAlchemy
- **Caching** : Singleton pour services (web_search, etc.)

### Scalabilité

- **Stateless API** : Pas de session serveur
- **Background jobs** : APScheduler pour tâches lourdes
- **Database indexing** : Index sur colonnes fréquemment requêtées

---

## Tests

### Structure

```
tests/
├── conftest.py              # Configuration pytest
├── test_events_idempotence.py
├── test_proposal_creation.py
├── test_apply_proposal.py
└── test_scheduler_reminder.py
```

### Exécution

```bash
cd backend
pytest tests/
```

---

## Maintenance

### Migrations DB

```bash
# Créer une migration
alembic revision -m "description"

# Appliquer migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Logs

- Logs backend : Console (stdout)
- Logs frontend : Console navigateur
- Logs d'exécution : Table `agent_execution_logs`

---

## Points d'attention

1. **Deux fichiers de config** : `app/config.py` et `app/core/config.py`
   - À unifier si possible

2. **Sessions sync/async** : Mélange de sessions synchrones et asynchrones
   - Normal pour compatibilité avec certains CRUD

3. **Modèles dupliqués** : `app/models/trigger.py` et `app/models/mindmap.py` (Trigger)
   - Le modèle dans `mindmap.py` est utilisé pour les relations

4. **Code mort** : Fichiers dans `_to_delete/` à supprimer après vérification

---

## Évolutions futures

### Améliorations possibles

- **Cache Redis** : Pour sessions et données fréquentes
- **WebSockets** : Notifications en temps réel
- **Queue system** : Pour traitement asynchrone (Celery, RQ)
- **Monitoring** : Prometheus + Grafana
- **CI/CD** : Pipeline automatisé
- **Docker** : Containerisation complète
- **Tests E2E** : Playwright ou Cypress

---

## Conclusion

L'architecture de **Personal Assistant** suit les meilleures pratiques modernes :
- Séparation claire des responsabilités
- API RESTful bien structurée
- Services réutilisables
- Extensibilité via agents configurables
- Automatisation via triggers et actions

Le code est organisé, maintenable et prêt pour l'évolution.
