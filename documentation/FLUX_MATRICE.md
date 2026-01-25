# Matrice des Flux et Interactions

Ce document décrit les flux de données et les interactions entre les différents composants de Personal Assistant.

## 📋 Table des matières

- [Flux principaux](#flux-principaux)
- [Matrice d'interactions](#matrice-dinteractions)
- [Séquences d'exécution](#séquences-dexécution)
- [Flux de données](#flux-de-données)
- [Diagrammes de flux](#diagrammes-de-flux)

---

## 🔄 Flux principaux

### 1. Flux d'authentification

```
Utilisateur → Frontend → API /api/auth/login
    ↓
Backend vérifie credentials
    ↓
Génère access_token + refresh_token
    ↓
Frontend stocke tokens (localStorage)
    ↓
Chaque requête inclut Authorization: Bearer <token>
    ↓
Backend valide token → Accès autorisé
```

**Composants impliqués** :
- `frontend/src/components/Auth/AuthProvider.tsx`
- `backend/app/api/routes/auth.py`
- `backend/app/auth/jwt_handler.py`
- `backend/app/core/deps.py` (get_current_user)

---

### 2. Flux de création d'un nœud

```
Utilisateur saisit texte → Frontend
    ↓
POST /api/nodes (avec token JWT)
    ↓
Backend: create_node()
    ↓
CRUD: crud_mindmap.create_node()
    ↓
DB: INSERT INTO nodes
    ↓
Agent IA: run_structurer_mindmap() (asynchrone)
    ↓
Création Proposal (structuration suggérée)
    ↓
Frontend: Affichage du nœud + proposition
    ↓
Utilisateur valide/modifie/rejette
    ↓
Si validé → Application de la structuration
```

**Composants impliqués** :
- `frontend/src/components/Mindmap/TextInput.tsx`
- `backend/app/api/routes/nodes.py`
- `backend/app/crud/mindmap.py`
- `backend/app/services/agent_structurer.py`
- `backend/app/services/proposals.py`

---

### 3. Flux d'exécution d'un agent IA

```
Utilisateur sélectionne agent + saisit input_text
    ↓
POST /api/configurable-agents/{id}/execute
    ↓
Backend: ConfigurableAgentService.execute_agent()
    ↓
Charge config agent depuis DB
    ↓
Crée agent Agno avec modèle OpenAI
    ↓
Configure outils (DuckDuckGo pour recherche web)
    ↓
Exécute agent.run(input_text)
    ↓
Agent utilise outils si nécessaire (recherche web)
    ↓
LLM génère réponse Markdown
    ↓
Parse sortie selon schéma
    ↓
Log exécution dans agent_execution_logs
    ↓
Retourne output_raw + output_parsed
    ↓
Frontend affiche résultat formaté (ReactMarkdown)
```

**Composants impliqués** :
- `frontend/src/components/Mindmap/NodeDetails.tsx`
- `backend/app/api/routes/configurable_agents.py`
- `backend/app/services/configurable_agent_service.py`
- `backend/app/tools/web_search_tools.py`
- `backend/app/models/configurable_agent.py`

---

### 4. Flux d'exécution d'un trigger automatique (cron)

```
APScheduler détecte trigger échu (selon expression cron)
    ↓
Appelle execute_trigger_with_config(trigger)
    ↓
Lit config: task_type, task_id, output_type, input_text
    ↓
Si task_type = "agent":
    → Charge agent depuis DB
    → Exécute ConfigurableAgentService.execute_agent()
    → Obtient résultat Markdown
    ↓
Si task_type = "action":
    → Exécute execute_actions_for_node()
    ↓
Si output_type = "email":
    → Formate résultat (Markdown → HTML)
    → Envoie via SMTP
    ↓
Sinon:
    → Log simplement l'exécution
    ↓
Met à jour trigger.last_fired_at
```

**Composants impliqués** :
- `backend/app/services/scheduler.py`
- `backend/app/services/configurable_agent_service.py`
- `backend/app/services/executor.py`
- `backend/app/services/email_smtp.py`

---

### 5. Flux de réception d'email

```
APScheduler (toutes les 2 min) → poll_imap()
    ↓
Connexion IMAP SSL
    ↓
Récupère emails UNSEEN
    ↓
Pour chaque email:
    → Vérifie idempotency_key (évite doublons)
    → Crée MailCache dans DB
    → Crée Node (status: inbox, source: email)
    → Crée Event (email_received)
    → Génère Proposal (structuration IA)
    → Marque email comme processed
    ↓
Commit transaction
```

**Composants impliqués** :
- `backend/app/services/scheduler.py` (poll_imap)
- `backend/app/services/email_imap.py`
- `backend/app/models/mail_cache.py`
- `backend/app/services/agent_structurer.py`

---

### 6. Flux de création d'un trigger

```
Utilisateur configure trigger dans NodeDetails
    ↓
Frontend: TriggerForm.tsx
    ↓
Génère expression cron (si trigger_type = cron)
    ↓
POST /api/triggers
    ↓
Backend: create_trigger()
    ↓
CRUD: crud_mindmap.create_trigger()
    ↓
DB: INSERT INTO triggers
    ↓
Si trigger_type = cron ET enabled = true:
    → Scheduler.reload_cron_triggers() (prochaine exécution dans 5 min)
    → Ajoute job APScheduler avec expression cron
    ↓
Retourne trigger créé
    ↓
Frontend affiche trigger dans la liste
```

**Composants impliqués** :
- `frontend/src/components/Trigger/TriggerForm.tsx`
- `backend/app/api/routes/triggers.py`
- `backend/app/crud/mindmap.py`
- `backend/app/services/scheduler.py`

---

## 📊 Matrice d'interactions

### Matrice Frontend ↔ Backend

| Composant Frontend | Endpoint Backend | Méthode | Données échangées |
|-------------------|-----------------|---------|-------------------|
| `AuthProvider` | `/api/auth/login` | POST | credentials → tokens |
| `AuthProvider` | `/api/auth/refresh` | POST | refresh_token → tokens |
| `AuthProvider` | `/api/auth/logout` | POST | refresh_token → void |
| `MindmapCanvas` | `/api/nodes` | GET | → nodes[] |
| `MindmapCanvas` | `/api/mindmaps` | GET | → mindmap |
| `TextInput` | `/api/nodes` | POST | node data → node |
| `NodeDetails` | `/api/nodes/{id}` | GET | → node |
| `NodeDetails` | `/api/nodes/{id}` | PUT | node data → node |
| `NodeDetails` | `/api/triggers/node/{id}` | GET | → triggers[] |
| `TriggerForm` | `/api/triggers` | POST | trigger data → trigger |
| `TriggerForm` | `/api/triggers/{id}` | PUT | trigger data → trigger |
| `NodeDetails` | `/api/triggers/{id}/execute` | POST | execute config → result |
| `AgentsList` | `/api/configurable-agents` | GET | → agents[] |
| `NodeDetails` | `/api/configurable-agents/{id}/execute` | POST | input_text → output |

---

### Matrice Backend ↔ Services externes

| Service Backend | Service Externe | Protocole | Données |
|----------------|----------------|-----------|---------|
| `email_imap.py` | Serveur IMAP | IMAP SSL (993) | Emails |
| `email_smtp.py` | Serveur SMTP | SMTP TLS (587) | Emails |
| `configurable_agent_service.py` | OpenAI API | HTTPS REST | Prompts → Réponses |
| `web_search_tools.py` | DuckDuckGo | HTTPS | Requêtes → Résultats |
| `web_search.py` | Google/Bing API | HTTPS REST | Requêtes → Résultats |

---

### Matrice Backend ↔ Base de données

| Service Backend | Table DB | Opérations | Fréquence |
|----------------|----------|------------|-----------|
| `crud/user.py` | `users` | CREATE, READ, UPDATE | Faible |
| `crud/mindmap.py` | `nodes` | CREATE, READ, UPDATE, DELETE | Élevée |
| `crud/mindmap.py` | `edges` | CREATE, READ, DELETE | Moyenne |
| `crud/mindmap.py` | `triggers` | CREATE, READ, UPDATE, DELETE | Moyenne |
| `crud/mindmap.py` | `actions` | CREATE, READ, UPDATE, DELETE | Faible |
| `crud/configurable_agent.py` | `configurable_agents` | CREATE, READ, UPDATE | Faible |
| `crud/configurable_agent.py` | `agent_execution_logs` | CREATE, READ | Élevée |
| `email_imap.py` | `mail_cache` | CREATE, READ, UPDATE | Toutes les 2 min |
| `scheduler.py` | `triggers` | READ, UPDATE | Toutes les 1-5 min |

---

## 🔀 Séquences d'exécution

### Séquence 1 : Exécution manuelle d'un agent

```
User → Frontend: Clic "Lancer" sur agent
Frontend → API: POST /api/configurable-agents/{id}/execute
API → ConfigurableAgentService: execute_agent()
ConfigurableAgentService → DB: get_agent_by_id()
ConfigurableAgentService → Agno: Crée agent avec modèle OpenAI
ConfigurableAgentService → Agno: agent.run(input_text)
Agno → OpenAI API: Chat completion request
OpenAI API → Agno: Réponse Markdown
Agno → ConfigurableAgentService: output_raw
ConfigurableAgentService → Parser: _parse_output()
Parser → ConfigurableAgentService: output_parsed
ConfigurableAgentService → DB: INSERT agent_execution_logs
ConfigurableAgentService → API: Retourne résultat
API → Frontend: JSON avec output_raw + output_parsed
Frontend → ReactMarkdown: Affiche résultat formaté
```

---

### Séquence 2 : Trigger cron automatique

```
APScheduler: Détecte trigger échu (cron expression)
APScheduler → scheduler.py: execute_trigger_with_config(trigger)
scheduler.py → DB: get_trigger() + get_agent_by_id()
scheduler.py → ConfigurableAgentService: execute_agent()
ConfigurableAgentService → Agno: Exécute agent
Agno → OpenAI API: Requête
OpenAI API → Agno: Réponse
Agno → ConfigurableAgentService: Résultat
ConfigurableAgentService → scheduler.py: Résultat
scheduler.py → email_smtp.py: format_agent_output_as_email()
email_smtp.py → scheduler.py: body_text + body_html
scheduler.py → email_smtp.py: send_email()
email_smtp.py → SMTP Server: Envoi email
scheduler.py → DB: UPDATE triggers.last_fired_at
```

---

### Séquence 3 : Réception et traitement d'email

```
APScheduler (toutes les 2 min) → scheduler.py: poll_imap()
scheduler.py → email_imap.py: fetch_unseen_messages()
email_imap.py → IMAP Server: Connexion SSL
IMAP Server → email_imap.py: Liste emails UNSEEN
email_imap.py → scheduler.py: messages[]
scheduler.py → _process_email_batch()
_process_email_batch → DB: Vérifie idempotency_key (MailCache)
_process_email_batch → DB: INSERT MailCache
_process_email_batch → DB: INSERT Node (status: inbox)
_process_email_batch → DB: INSERT Event (email_received)
_process_email_batch → agent_structurer.py: run_structurer_mindmap()
agent_structurer.py → OpenAI API: Analyse texte
OpenAI API → agent_structurer.py: Proposition structuration
agent_structurer.py → proposals.py: create_proposal()
proposals.py → DB: INSERT Proposal
_process_email_batch → DB: UPDATE MailCache.processed = true
scheduler.py → DB: COMMIT transaction
```

---

### Séquence 4 : Création et activation d'un trigger cron

```
User → Frontend: Configure trigger cron dans TriggerForm
Frontend → TriggerForm: generateCronExpression()
TriggerForm → Frontend: cron_expression généré
User → Frontend: Clic "Sauvegarder"
Frontend → API: POST /api/triggers
API → crud_mindmap.py: create_trigger()
crud_mindmap.py → DB: INSERT INTO triggers
crud_mindmap.py → API: Retourne trigger créé
API → Frontend: trigger créé
Frontend → User: Confirmation
(En arrière-plan)
APScheduler (toutes les 5 min) → scheduler.py: reload_cron_triggers()
scheduler.py → DB: SELECT triggers WHERE type=cron AND enabled=true
scheduler.py → Pour chaque trigger:
    → parse_cron_expression()
    → APScheduler.add_job() avec expression cron
APScheduler: Job programmé pour exécution future
```

---

## 📈 Flux de données

### Flux de données : Nœud

```
Création (TextInput/Email/API)
    ↓
Node (raw_text, status: inbox)
    ↓
Agent IA analyse
    ↓
Proposal généré
    ↓
Utilisateur valide/modifie
    ↓
Node structuré (type, tags, relations)
    ↓
Affichage dans MindmapCanvas
    ↓
Modifications possibles (titre, statut, tags)
    ↓
Node final (status: done)
```

---

### Flux de données : Trigger

```
Création (TriggerForm)
    ↓
Trigger (config: {task_type, task_id, cron_expression, ...})
    ↓
Sauvegarde DB
    ↓
Chargement dans APScheduler (si cron)
    ↓
Exécution automatique (selon cron)
    ↓
Résultat (output_raw, output_parsed)
    ↓
Rendu (screen ou email)
    ↓
Log (last_fired_at mis à jour)
```

---

### Flux de données : Agent IA

```
Configuration (fichier .md)
    ↓
Parsing (AgentConfigParser)
    ↓
ConfigurableAgent (persona, instructions, schema, tools)
    ↓
Sauvegarde DB
    ↓
Exécution (execute_agent)
    ↓
Agent Agno créé (avec modèle OpenAI)
    ↓
Exécution avec outils (recherche web si nécessaire)
    ↓
Réponse LLM (Markdown)
    ↓
Parsing selon schéma
    ↓
Log exécution (agent_execution_logs)
    ↓
Résultat retourné (output_raw + output_parsed)
```

---

## 🎨 Diagrammes de flux

### Diagramme de flux : Cycle de vie d'un nœud

```
┌─────────────┐
│  Création   │ (TextInput, Email, API)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Inbox     │ (status: inbox)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Proposition │ (Agent IA suggère structuration)
│    IA       │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Validation  │ (Utilisateur valide/modifie/rejette)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Structuré   │ (type, tags, relations définis)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Ready     │ (status: ready)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Doing     │ (status: doing)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│    Done     │ (status: done)
└─────────────┘
```

---

### Diagramme de flux : Exécution d'un trigger

```
┌─────────────────┐
│  Trigger créé   │
│  (cron/date/...) │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  APScheduler    │ (Détecte déclenchement)
│  détecte échéance│
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Lecture config │ (task_type, task_id, output_type)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ↓         ↓
┌────────┐ ┌────────┐
│ Agent  │ │ Action │
└───┬────┘ └───┬────┘
    │          │
    └────┬─────┘
         │
         ↓
┌─────────────────┐
│  Exécution      │ (Agent ou Action)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Résultat       │ (output_raw, output_parsed)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ↓         ↓
┌────────┐ ┌────────┐
│ Screen │ │ Email  │
└────────┘ └────────┘
```

---

### Diagramme de flux : Architecture des composants

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Mindmap  │  │ Triggers │  │  Agents  │  │  Auth   │ │
│  │  Canvas  │  │   Form   │  │   List   │  │ Provider│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│       │             │              │             │       │
│       └─────────────┼──────────────┼─────────────┘       │
│                     │              │                     │
│              ┌──────▼──────────────▼──────┐              │
│              │     API Client (axios)     │              │
│              └─────────────┬──────────────┘              │
└────────────────────────────┼─────────────────────────────┘
                             │ HTTP/REST + JWT
┌────────────────────────────▼─────────────────────────────┐
│                    Backend (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ API Routes   │  │   Services   │  │     CRUD     │   │
│  │ (auth, nodes, │  │ (agents,     │  │  (mindmap,  │   │
│  │  triggers)    │  │  scheduler,  │  │   user)     │   │
│  │               │  │  email)      │  │             │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘   │
│         │                 │                  │           │
│         └─────────────────┼──────────────────┘           │
│                           │                              │
│                    ┌──────▼──────┐                       │
│                    │   Models    │                       │
│                    │ (SQLAlchemy)│                       │
│                    └──────┬──────┘                       │
└───────────────────────────┼──────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────┐
│                    PostgreSQL                            │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│  │ users  │ │ nodes  │ │triggers│ │agents  │ │ logs   │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│              Services Externes                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ OpenAI   │  │  IMAP    │  │  SMTP    │  │DuckDuckGo│   │
│  │   API    │  │ Server   │  │ Server   │  │   API    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────────────────────────────────────────────┘
```

---

## 🔍 Matrice de dépendances

### Dépendances entre services

| Service | Dépend de | Type | Description |
|---------|-----------|------|-------------|
| `configurable_agent_service` | `agent_config_parser` | Import direct | Parse config Markdown |
| `configurable_agent_service` | `OpenAI API` | HTTP | Exécution agents |
| `scheduler` | `email_imap` | Import direct | Polling emails |
| `scheduler` | `configurable_agent_service` | Import direct | Exécution triggers |
| `scheduler` | `executor` | Import direct | Exécution actions |
| `email_smtp` | `SMTP Server` | SMTP | Envoi emails |
| `web_search_tools` | `DuckDuckGo API` | HTTP | Recherche web |
| `agent_structurer` | `OpenAI API` | HTTP | Structuration IA |
| `proposals` | `agent_structurer` | Import direct | Création propositions |

---

## 📝 Notes importantes

### Points d'attention

1. **Sessions DB** : Mélange de sessions sync (CRUD) et async (services)
   - Les CRUD utilisent `SessionLocal()` (sync)
   - Les services utilisent `AsyncSessionLocal()` (async)
   - Attention aux conversions UUID ↔ Integer

2. **Idempotence** : 
   - Emails : `idempotency_key` basé sur `Message-ID`
   - Events : `idempotency_key` pour éviter doublons
   - Triggers : `dedupe_key` pour éviter exécutions multiples

3. **Scheduler** :
   - Jobs asynchrones (APScheduler AsyncIOScheduler)
   - Rechargement des triggers cron toutes les 5 min
   - Polling IMAP toutes les 2 min

4. **Parsing Markdown/JSON** :
   - Détection automatique du format (Markdown vs JSON)
   - Nettoyage des caractères de contrôle
   - Fallback sur Markdown brut si parsing JSON échoue

---

## 🔄 Flux de synchronisation

### Synchronisation Frontend ↔ Backend

- **État local** : Zustand stores (`authStore`, `mindmapStore`)
- **Synchronisation** : Polling ou WebSockets (à implémenter)
- **Cache** : Pas de cache côté frontend actuellement
- **Optimistic updates** : Non implémenté (à ajouter)

---

**Dernière mise à jour** : 2026-01-22  
**Maintenu par** : Équipe de développement
