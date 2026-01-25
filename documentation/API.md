# Documentation de l'API REST

Cette documentation décrit l'ensemble des endpoints de l'API REST de Personal Assistant.

**Base URL** : `http://localhost:8000`

**Authentification** : Tous les endpoints (sauf `/api/auth/*`) nécessitent un token JWT dans le header :
```
Authorization: Bearer <access_token>
```

---

## 🔐 Authentification

### POST `/api/auth/register`

Création d'un nouveau compte utilisateur.

**Request Body** :
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

**Response** (201) :
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### POST `/api/auth/login`

Connexion d'un utilisateur existant.

**Request Body** :
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response** (200) :
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### POST `/api/auth/refresh`

Renouvelle l'access token à partir d'un refresh token.

**Request Body** :
```json
{
  "refresh_token": "eyJ..."
}
```

**Response** (200) :
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### POST `/api/auth/logout`

Déconnexion : invalide le refresh token.

**Request Body** :
```json
{
  "refresh_token": "eyJ..."
}
```

**Response** (200) :
```json
{
  "message": "Déconnexion réussie"
}
```

---

## 👤 Utilisateurs

### GET `/api/users/me`

Récupère les informations de l'utilisateur actuellement connecté.

**Response** (200) :
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00"
}
```

---

## 🗺️ Mindmaps

### GET `/api/mindmaps`

Récupère la liste des mindmaps de l'utilisateur.

**Query Parameters** :
- `skip` (int, default: 0) : Nombre d'éléments à sauter
- `limit` (int, default: 100) : Nombre d'éléments à retourner

**Response** (200) :
```json
[
  {
    "id": 1,
    "name": "Mon Mindmap",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

### GET `/api/mindmaps/{mindmap_id}`

Récupère un mindmap avec ses nœuds et arêtes.

**Response** (200) :
```json
{
  "id": 1,
  "name": "Mon Mindmap",
  "nodes": [...],
  "edges": [...],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### POST `/api/mindmaps`

Crée un nouveau mindmap.

**Request Body** :
```json
{
  "name": "Nouveau Mindmap"
}
```

**Response** (201) :
```json
{
  "id": 1,
  "name": "Nouveau Mindmap",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### PUT `/api/mindmaps/{mindmap_id}`

Met à jour un mindmap.

**Request Body** :
```json
{
  "name": "Mindmap modifié"
}
```

**Response** (200) :
```json
{
  "id": 1,
  "name": "Mindmap modifié",
  "updated_at": "2024-01-01T00:00:00"
}
```

### DELETE `/api/mindmaps/{mindmap_id}`

Supprime un mindmap.

**Response** (204) : No content

---

## 📝 Nœuds (Nodes)

### GET `/api/nodes`

Récupère la liste des nœuds.

**Query Parameters** :
- `skip` (int, default: 0)
- `limit` (int, default: 100)
- `status` (string, optional) : Filtrer par statut
- `type` (string, optional) : Filtrer par type

**Response** (200) :
```json
[
  {
    "id": "uuid",
    "raw_text": "Texte du nœud",
    "title": "Titre",
    "type": "task",
    "status": "inbox",
    "tags": ["urgent", "backend"],
    "position": {"x": 100, "y": 200},
    "created_at": "2024-01-01T00:00:00"
  }
]
```

### GET `/api/nodes/{node_id}`

Récupère un nœud avec ses enfants.

**Response** (200) :
```json
{
  "id": "uuid",
  "raw_text": "Texte du nœud",
  "title": "Titre",
  "type": "task",
  "status": "inbox",
  "children": [...],
  "created_at": "2024-01-01T00:00:00"
}
```

### POST `/api/nodes`

Crée un nouveau nœud.

**Request Body** :
```json
{
  "raw_text": "Nouveau nœud",
  "type": "idea",
  "status": "inbox",
  "tags": ["tag1"],
  "position": {"x": 0, "y": 0}
}
```

**Response** (201) :
```json
{
  "id": "uuid",
  "raw_text": "Nouveau nœud",
  "type": "idea",
  "status": "inbox",
  "created_at": "2024-01-01T00:00:00"
}
```

### PUT `/api/nodes/{node_id}`

Met à jour un nœud.

**Request Body** :
```json
{
  "title": "Titre modifié",
  "status": "doing",
  "tags": ["tag1", "tag2"]
}
```

**Response** (200) :
```json
{
  "id": "uuid",
  "title": "Titre modifié",
  "status": "doing",
  "updated_at": "2024-01-01T00:00:00"
}
```

### DELETE `/api/nodes/{node_id}`

Supprime un nœud.

**Response** (200) :
```json
{
  "message": "Nœud supprimé avec succès"
}
```

---

## ⚡ Triggers (Déclencheurs)

### GET `/api/triggers/node/{node_id}`

Récupère tous les triggers d'un nœud.

**Response** (200) :
```json
[
  {
    "id": "uuid",
    "node_id": "uuid",
    "trigger_type": "cron",
    "config": {
      "task_type": "agent",
      "selected_agent": 1,
      "input_text": "Recherche actualités IA",
      "output_type": "email",
      "cron_expression": "0 9 * * 1,3,5"
    },
    "enabled": true,
    "last_fired_at": "2024-01-01T09:00:00"
  }
]
```

### GET `/api/triggers/{trigger_id}`

Récupère un trigger avec ses actions.

**Response** (200) :
```json
{
  "id": "uuid",
  "node_id": "uuid",
  "trigger_type": "cron",
  "config": {...},
  "enabled": true,
  "actions": [...]
}
```

### POST `/api/triggers`

Crée un nouveau trigger.

**Request Body** :
```json
{
  "node_id": "uuid",
  "trigger_type": "cron",
  "config": {
    "task_type": "agent",
    "selected_agent": 1,
    "input_text": "Recherche actualités IA",
    "output_type": "email",
    "email_to": "user@example.com",
    "email_subject": "Rapport de veille",
    "cron_expression": "0 9 * * 1,3,5"
  },
  "enabled": true
}
```

**Response** (201) :
```json
{
  "id": "uuid",
  "node_id": "uuid",
  "trigger_type": "cron",
  "config": {...},
  "enabled": true
}
```

### PUT `/api/triggers/{trigger_id}`

Met à jour un trigger.

**Request Body** :
```json
{
  "config": {
    "cron_expression": "0 10 * * 1,3,5"
  },
  "enabled": false
}
```

**Response** (200) :
```json
{
  "id": "uuid",
  "config": {...},
  "enabled": false
}
```

### DELETE `/api/triggers/{trigger_id}`

Supprime un trigger.

**Response** (204) : No content

### POST `/api/triggers/{trigger_id}/execute`

Exécute un trigger manuellement.

**Request Body** :
```json
{
  "input_text": "Texte d'entrée personnalisé (optionnel)",
  "output_type": "screen"
}
```

**Response** (200) :
```json
{
  "success": true,
  "output": {
    "output_raw": "# Rapport de veille\n\n...",
    "output_parsed": {
      "markdown": "# Rapport de veille\n\n...",
      "format": "markdown"
    },
    "execution_time_ms": 25000
  },
  "email_sent": false
}
```

---

## 🤖 Agents configurables

### GET `/api/configurable-agents`

Récupère la liste des agents configurables.

**Response** (200) :
```json
[
  {
    "id": 1,
    "name": "News Monitor Agent",
    "slug": "news-monitor",
    "description": "Agent de veille informationnelle",
    "persona": "Journaliste spécialisé...",
    "tools": ["web_search", "web_search_news"]
  }
]
```

### GET `/api/configurable-agents/{agent_id}`

Récupère un agent configurable.

**Response** (200) :
```json
{
  "id": 1,
  "name": "News Monitor Agent",
  "slug": "news-monitor",
  "description": "Agent de veille informationnelle",
  "prompt_template": "...",
  "output_schema": {...},
  "persona": "...",
  "instructions": "...",
  "tools": ["web_search", "web_search_news"]
}
```

### POST `/api/configurable-agents/{agent_id}/execute`

Exécute un agent configurable.

**Request Body** :
```json
{
  "input_text": "Recherche l'actualité Agentique IA ainsi que les nouveautés IA de la semaine."
}
```

**Response** (200) :
```json
{
  "success": true,
  "output": {
    "output_raw": "# Rapport de veille\n\n## Thème\n...",
    "output_parsed": {
      "markdown": "# Rapport de veille\n\n...",
      "format": "markdown"
    },
    "execution_time_ms": 34264,
    "prompt_used": "Persona: Journaliste..."
  }
}
```

---

## 🎯 Actions

### GET `/api/actions/trigger/{trigger_id}`

Récupère toutes les actions d'un trigger.

**Response** (200) :
```json
[
  {
    "id": 1,
    "trigger_id": "uuid",
    "type": "send_email",
    "order": 1,
    "enabled": true,
    "config": {
      "to": "user@example.com",
      "subject": "Notification",
      "body": "Contenu de l'email"
    }
  }
]
```

### POST `/api/actions`

Crée une nouvelle action.

**Request Body** :
```json
{
  "trigger_id": "uuid",
  "type": "send_email",
  "order": 1,
  "enabled": true,
  "config": {
    "to": "user@example.com",
    "subject": "Notification",
    "body": "Contenu de l'email"
  }
}
```

**Response** (201) :
```json
{
  "id": 1,
  "trigger_id": "uuid",
  "type": "send_email",
  "order": 1,
  "enabled": true
}
```

### PUT `/api/actions/{action_id}`

Met à jour une action.

**Request Body** :
```json
{
  "enabled": false,
  "config": {
    "subject": "Nouveau sujet"
  }
}
```

**Response** (200) :
```json
{
  "id": 1,
  "enabled": false,
  "config": {...}
}
```

### DELETE `/api/actions/{action_id}`

Supprime une action.

**Response** (204) : No content

---

## 📧 Ingestion de texte

### POST `/api/ingest/text`

Ingère un texte et crée un nœud avec proposition de structuration.

**Request Body** :
```json
{
  "text": "Texte à ingérer et structurer"
}
```

**Response** (200) :
```json
{
  "node_id": "uuid",
  "proposal_id": "uuid",
  "message": "Texte ingéré avec succès"
}
```

---

## 🔍 Recherche web (MCP)

### POST `/api/web-search`

Recherche web via le serveur MCP.

**Request Body** :
```json
{
  "query": "Actualités IA Agentique",
  "type": "web" // ou "news"
}
```

**Response** (200) :
```json
{
  "results": [
    {
      "title": "Titre de l'article",
      "url": "https://example.com/article",
      "snippet": "Extrait de l'article...",
      "source": "Example.com",
      "date": "2024-01-01"
    }
  ]
}
```

---

## 📊 Codes de statut HTTP

| Code | Signification |
|------|---------------|
| 200 | Succès |
| 201 | Créé avec succès |
| 204 | Succès sans contenu |
| 400 | Requête invalide |
| 401 | Non authentifié |
| 403 | Accès interdit |
| 404 | Ressource introuvable |
| 422 | Erreur de validation |
| 500 | Erreur serveur |

---

## 🔒 Gestion des erreurs

Toutes les erreurs suivent le format standard :

```json
{
  "detail": "Message d'erreur détaillé"
}
```

**Exemples** :

- **401 Unauthorized** :
```json
{
  "detail": "Token invalide ou expiré"
}
```

- **404 Not Found** :
```json
{
  "detail": "Ressource introuvable"
}
```

- **422 Validation Error** :
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 📚 Documentation interactive

Une documentation interactive (Swagger UI) est disponible à :
- **Swagger UI** : `http://localhost:8000/docs`
- **ReDoc** : `http://localhost:8000/redoc`

Ces interfaces permettent de :
- Explorer tous les endpoints
- Tester les requêtes directement
- Voir les schémas de données
- Comprendre les paramètres requis

---

## 🔄 Rate Limiting

Actuellement, aucun rate limiting n'est implémenté. À prévoir pour la production.

---

## 📝 Notes importantes

1. **UUIDs** : Les IDs de nœuds, triggers et actions sont des UUIDs (format string)
2. **Dates** : Toutes les dates sont au format ISO 8601 (UTC)
3. **Pagination** : Utilisez `skip` et `limit` pour paginer les résultats
4. **Filtres** : Certains endpoints supportent des filtres via query parameters
5. **Relations** : Les relations entre entités sont chargées à la demande (lazy loading)

---

## 🧪 Exemples d'utilisation

### Exemple complet : Créer un trigger cron

```bash
# 1. Se connecter
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Réponse : {"access_token": "eyJ...", "refresh_token": "eyJ..."}

# 2. Créer un trigger
curl -X POST http://localhost:8000/api/triggers \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "uuid-du-node",
    "trigger_type": "cron",
    "config": {
      "task_type": "agent",
      "selected_agent": 1,
      "input_text": "Recherche actualités IA",
      "output_type": "email",
      "email_to": "user@example.com",
      "cron_expression": "0 9 * * 1,3,5"
    },
    "enabled": true
  }'
```

---

Pour plus d'informations sur l'architecture et les fonctionnalités, consultez :
- [Documentation d'Architecture](ARCHITECTURE.md)
- [Documentation Fonctionnelle](FUNCTIONAL.md)
