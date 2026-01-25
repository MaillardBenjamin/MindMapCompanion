# Diagrammes Mermaid

Ce document contient les diagrammes de classe et de séquence principaux de Personal Assistant, générés avec Mermaid.

## 📋 Table des matières

- [Diagrammes de classe](#diagrammes-de-classe)
- [Diagrammes de séquence](#diagrammes-de-séquence)
- [Diagrammes d'activité](#diagrammes-dactivité)

---

## 🏗️ Diagrammes de classe

### Modèles de domaine principaux

```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String hashed_password
        +String name
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +List~ConfigurableAgent~ configurable_agents
        +List~RefreshToken~ refresh_tokens
    }x

    class Node {
        +UUID id
        +String raw_text
        +String title
        +NodeType type
        +NodeStatus status
        +String domain
        +List~String~ tags
        +String next_action
        +NodeSource source
        +Dict source_ref
        +Dict position
        +Dict ai_meta
        +DateTime created_at
        +DateTime updated_at
    }

    class Edge {
        +UUID id
        +UUID from_node_id
        +UUID to_node_id
        +EdgeRelationType relation_type
        +Float confidence
        +CreatedBy created_by
        +DateTime created_at
    }

    class Trigger {
        +UUID id
        +UUID node_id
        +TriggerType trigger_type
        +Dict config
        +Boolean enabled
        +String last_fired_at
        +String dedupe_key
    }

    class Action {
        +UUID id
        +UUID trigger_id
        +ActionType type
        +Integer order
        +Boolean enabled
        +Dict config
    }

    class ConfigurableAgent {
        +Integer id
        +Integer user_id
        +String name
        +String slug
        +String description
        +String markdown_config
        +String prompt_template
        +JSON output_schema
        +JSON tools
        +JSON mcp_servers
        +String persona
        +String instructions
        +Boolean is_active
        +Boolean is_public
        +DateTime created_at
        +DateTime updated_at
    }

    class AgentExecutionLog {
        +Integer id
        +Integer agent_id
        +Integer user_id
        +String input_text
        +String prompt_used
        +String output_raw
        +JSON output_parsed
        +Boolean success
        +String error_message
        +Integer execution_time_ms
        +DateTime created_at
    }

    class Proposal {
        +UUID id
        +UUID node_id
        +String agent_name
        +JSON proposal_json
        +ProposalStatus status
        +String reviewed_by
        +DateTime reviewed_at
        +DateTime created_at
    }

    class MailCache {
        +UUID id
        +MailProvider provider
        +String provider_message_id
        +String from_addr
        +String subject
        +String snippet
        +DateTime received_at
        +String raw_payload
        +Boolean processed
        +String idempotency_key
    }

    class Event {
        +UUID event_id
        +EventType event_type
        +String idempotency_key
        +JSON payload
        +DateTime created_at
    }

    User "1" --> "*" ConfigurableAgent : owns
    User "1" --> "*" AgentExecutionLog : executes
    Node "1" --> "*" Edge : from_node
    Node "1" --> "*" Edge : to_node
    Node "1" --> "*" Trigger : has
    Trigger "1" --> "*" Action : has
    ConfigurableAgent "1" --> "*" AgentExecutionLog : logs
    Node "1" --> "*" Proposal : has
```

---

### Services et couches applicatives

```mermaid
classDiagram
    class ConfigurableAgentService {
        -Settings settings
        -AgentConfigParser parser
        +execute_agent(db, agent_id, user_id, input_text, options)
        -_create_agent(config) Agent
        -_parse_output(output_raw, output_schema) Dict
    }

    class AgentConfigParser {
        +parse_markdown(markdown_content) Dict
        -_parse_frontmatter(frontmatter) Dict
        -_parse_sections(content) Dict
        -_parse_json_schema(schema_text) Dict
        -_parse_list(list_text) List
    }

    class Scheduler {
        +start_scheduler() AsyncIOScheduler
        +poll_imap() None
        +run_due_triggers() None
        +load_cron_triggers(scheduler) None
        +execute_trigger_with_config(trigger) None
        +parse_cron_expression(cron_expr) Dict
    }

    class EmailIMAPService {
        +fetch_unseen_messages() List~Dict~
        -_connect() IMAP4_SSL
    }

    class EmailSMTPService {
        +send_email(to_email, subject, body_text, body_html) Boolean
        +format_agent_output_as_email(output_raw, output_parsed, ...) Tuple
    }

    class WebSearchService {
        +search(query, search_type) List~WebSearchResult~
        -_search_google(query) List
        -_search_bing(query) List
        -_mock_search(query) List
    }

    class AgentStructurerService {
        +run_structurer_mindmap(text, context) Dict
    }

    class ExecutorService {
        +execute_actions_for_node(session, node_id, trigger_id) None
    }

    class ProposalsService {
        +create_proposal(session, node_id, agent_name, proposal_json) Proposal
        +apply_proposal(session, proposal, reviewed_by) Proposal
    }

    ConfigurableAgentService --> AgentConfigParser : uses
    ConfigurableAgentService --> WebSearchService : uses
    Scheduler --> EmailIMAPService : uses
    Scheduler --> ConfigurableAgentService : uses
    Scheduler --> ExecutorService : uses
    Scheduler --> EmailSMTPService : uses
    AgentStructurerService --> ProposalsService : creates
```

---

### Couche API (Routes)

```mermaid
classDiagram
    class AuthRouter {
        +POST /api/auth/register()
        +POST /api/auth/login()
        +POST /api/auth/refresh()
        +POST /api/auth/logout()
    }

    class NodesRouter {
        +GET /api/nodes()
        +POST /api/nodes()
        +GET /api/nodes/{id}()
        +PUT /api/nodes/{id}()
        +DELETE /api/nodes/{id}()
    }

    class TriggersRouter {
        +GET /api/triggers/node/{node_id}()
        +POST /api/triggers()
        +GET /api/triggers/{id}()
        +PUT /api/triggers/{id}()
        +DELETE /api/triggers/{id}()
        +POST /api/triggers/{id}/execute()
    }

    class ConfigurableAgentsRouter {
        +GET /api/configurable-agents()
        +GET /api/configurable-agents/{id}()
        +POST /api/configurable-agents/{id}/execute()
    }

    class CRUDMindmap {
        +create_node(db, node_data, user_id) Node
        +get_node(db, node_id, user_id) Node
        +update_node(db, node_id, node_data, user_id) Node
        +delete_node(db, node_id, user_id) Boolean
        +create_trigger(db, trigger_data, user_id) Trigger
        +get_triggers_by_node(db, node_id, user_id) List~Trigger~
    }

    AuthRouter --> CRUDMindmap : uses
    NodesRouter --> CRUDMindmap : uses
    TriggersRouter --> CRUDMindmap : uses
    ConfigurableAgentsRouter --> ConfigurableAgentService : uses
    TriggersRouter --> ConfigurableAgentService : uses
    TriggersRouter --> ExecutorService : uses
```

---

## 🔄 Diagrammes de séquence

### Séquence : Exécution manuelle d'un agent IA

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant F as Frontend
    participant API as API Router
    participant CAS as ConfigurableAgentService
    participant DB as Database
    participant A as Agno Agent
    participant OAI as OpenAI API
    participant WS as WebSearch

    U->>F: Sélectionne agent + saisit input_text
    F->>API: POST /api/configurable-agents/{id}/execute
    API->>CAS: execute_agent(agent_id, user_id, input_text)
    CAS->>DB: get_agent_by_id(agent_id)
    DB-->>CAS: ConfigurableAgent
    CAS->>CAS: _create_agent(config)
    CAS->>A: Crée agent Agno avec modèle OpenAI
    CAS->>A: agent.run(input_text)
    
    alt Outils de recherche demandés
        A->>WS: Recherche web (DuckDuckGo)
        WS-->>A: Résultats de recherche
    end
    
    A->>OAI: Chat completion request
    OAI-->>A: Réponse Markdown
    A-->>CAS: output_raw (Markdown)
    CAS->>CAS: _parse_output(output_raw, schema)
    CAS-->>CAS: output_parsed (JSON)
    CAS->>DB: INSERT agent_execution_logs
    CAS-->>API: Résultat (output_raw + output_parsed)
    API-->>F: JSON response
    F->>F: ReactMarkdown.render(output_raw)
    F-->>U: Affiche résultat formaté
```

---

### Séquence : Exécution automatique d'un trigger cron

```mermaid
sequenceDiagram
    participant APS as APScheduler
    participant SCH as Scheduler
    participant DB as Database
    participant CAS as ConfigurableAgentService
    participant A as Agno Agent
    participant OAI as OpenAI API
    participant SMTP as EmailSMTP
    participant U as Utilisateur (Email)

    APS->>SCH: Déclenchement (expression cron)
    SCH->>DB: SELECT triggers WHERE type=cron AND enabled=true
    DB-->>SCH: Trigger[]
    
    loop Pour chaque trigger échu
        SCH->>SCH: execute_trigger_with_config(trigger)
        SCH->>DB: get_trigger() + get_agent_by_id()
        DB-->>SCH: Trigger + ConfigurableAgent
        
        alt task_type = "agent"
            SCH->>CAS: execute_agent(agent_id, user_id, input_text)
            CAS->>A: Crée et exécute agent
            A->>OAI: Requête LLM
            OAI-->>A: Réponse Markdown
            A-->>CAS: output_raw
            CAS-->>SCH: Résultat
            
            alt output_type = "email"
                SCH->>SMTP: format_agent_output_as_email()
                SMTP-->>SCH: body_text + body_html
                SCH->>SMTP: send_email(to, subject, body)
                SMTP->>U: Email envoyé
            end
        else task_type = "action"
            SCH->>SCH: execute_actions_for_node()
        end
        
        SCH->>DB: UPDATE triggers.last_fired_at
    end
```

---

### Séquence : Réception et traitement d'un email

```mermaid
sequenceDiagram
    participant APS as APScheduler
    participant SCH as Scheduler
    participant IMAP as EmailIMAP
    participant IMAP_S as IMAP Server
    participant DB as Database
    participant AS as AgentStructurer
    participant OAI as OpenAI API
    participant PRO as ProposalsService

    APS->>SCH: Toutes les 2 min: poll_imap()
    SCH->>IMAP: fetch_unseen_messages()
    IMAP->>IMAP_S: Connexion SSL (port 993)
    IMAP_S-->>IMAP: Liste emails UNSEEN
    IMAP-->>SCH: messages[]
    
    SCH->>SCH: _process_email_batch(session, messages)
    
    loop Pour chaque email
        SCH->>DB: Vérifie idempotency_key (MailCache)
        alt Email déjà traité
            SCH->>SCH: Skip (idempotence)
        else Nouvel email
            SCH->>DB: INSERT MailCache
            SCH->>DB: INSERT Node (status: inbox, source: email)
            SCH->>DB: INSERT Event (email_received)
            SCH->>AS: run_structurer_mindmap(raw_text, context)
            AS->>OAI: Analyse texte + contexte
            OAI-->>AS: Proposition structuration
            AS-->>SCH: proposal_json
            SCH->>PRO: create_proposal(node_id, "StructurerMindmap", proposal_json)
            PRO->>DB: INSERT Proposal
            SCH->>DB: UPDATE MailCache.processed = true
        end
    end
    
    SCH->>DB: COMMIT transaction
```

---

### Séquence : Création et validation d'une proposition de structuration

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant F as Frontend
    participant API as API Router
    participant DB as Database
    participant PRO as ProposalsService
    participant CRUD as CRUDMindmap

    Note over U,DB: Création automatique de proposition
    DB->>PRO: Node créé (status: inbox)
    PRO->>PRO: create_proposal(node_id, agent_name, proposal_json)
    PRO->>DB: INSERT Proposal (status: pending)
    
    Note over U,DB: Utilisateur consulte la proposition
    U->>F: Ouvre NodeDetails
    F->>API: GET /api/nodes/{id}
    API->>CRUD: get_node(node_id)
    CRUD->>DB: SELECT node + proposals
    DB-->>CRUD: Node + Proposal[]
    CRUD-->>API: NodeWithProposals
    API-->>F: JSON response
    F-->>U: Affiche proposition
    
    Note over U,DB: Utilisateur valide/modifie/rejette
    alt Validation
        U->>F: Clic "Approuver"
        F->>API: POST /api/proposals/{id}/apply
        API->>PRO: apply_proposal(proposal_id, reviewed_by)
        PRO->>DB: UPDATE Proposal (status: approved)
        PRO->>CRUD: update_node() avec structuration
        CRUD->>DB: UPDATE Node (type, tags, relations)
        PRO-->>API: Proposal appliqué
        API-->>F: Confirmation
        F-->>U: Nœud structuré
    else Modification
        U->>F: Modifie proposition
        F->>API: POST /api/proposals/{id}/apply (avec modifications)
        API->>PRO: apply_proposal() avec modifications
        PRO->>DB: UPDATE Node avec modifications
        PRO-->>API: Confirmation
        API-->>F: Confirmation
        F-->>U: Nœud structuré avec modifications
    else Rejet
        U->>F: Clic "Rejeter"
        F->>API: POST /api/proposals/{id}/reject
        API->>PRO: reject_proposal(proposal_id)
        PRO->>DB: UPDATE Proposal (status: rejected)
        PRO-->>API: Confirmation
        API-->>F: Confirmation
        F-->>U: Proposition rejetée
    end
```

---

### Séquence : Authentification et gestion des tokens

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant F as Frontend
    participant API as API Router
    participant AUTH as AuthService
    participant JWT as JWT Handler
    participant DB as Database

    Note over U,DB: Login initial
    U->>F: Saisit email + password
    F->>API: POST /api/auth/login
    API->>AUTH: verify_credentials(email, password)
    AUTH->>DB: SELECT user WHERE email=?
    DB-->>AUTH: User
    AUTH->>AUTH: verify_password(password, hashed_password)
    AUTH->>JWT: create_access_token(user_data)
    JWT-->>AUTH: access_token
    AUTH->>JWT: create_refresh_token(user_data)
    JWT-->>AUTH: refresh_token
    AUTH->>DB: INSERT refresh_token
    AUTH-->>API: Tokens
    API-->>F: {access_token, refresh_token}
    F->>F: localStorage.setItem("tokens")
    F-->>U: Authentifié
    
    Note over U,DB: Requêtes suivantes
    U->>F: Action nécessitant auth
    F->>F: Récupère access_token
    F->>API: GET /api/... (Header: Authorization: Bearer token)
    API->>JWT: verify_token(token)
    JWT-->>API: user_data (valide)
    API->>API: Traite la requête
    API-->>F: Réponse
    
    Note over U,DB: Token expiré - Refresh
    F->>API: GET /api/... (token expiré)
    API->>JWT: verify_token(token)
    JWT-->>API: TokenExpiredError
    API-->>F: 401 Unauthorized
    F->>F: Récupère refresh_token
    F->>API: POST /api/auth/refresh
    API->>AUTH: verify_refresh_token(refresh_token)
    AUTH->>DB: SELECT refresh_token WHERE token=?
    DB-->>AUTH: RefreshToken (valide)
    AUTH->>JWT: create_access_token(user_data)
    JWT-->>AUTH: Nouveau access_token
    AUTH->>JWT: create_refresh_token(user_data)
    JWT-->>AUTH: Nouveau refresh_token (rotation)
    AUTH->>DB: UPDATE refresh_token (rotation)
    AUTH-->>API: Nouveaux tokens
    API-->>F: {access_token, refresh_token}
    F->>F: localStorage.setItem("tokens")
    F->>API: Retry requête originale avec nouveau token
    API-->>F: Réponse
```

---

### Séquence : Création d'un trigger cron

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant F as Frontend
    participant TF as TriggerForm
    participant API as API Router
    participant CRUD as CRUDMindmap
    participant DB as Database
    participant SCH as Scheduler
    participant APS as APScheduler

    U->>F: Configure trigger dans NodeDetails
    F->>TF: Ouvre TriggerForm
    U->>TF: Sélectionne type "cron"
    U->>TF: Configure heure (9h), minute (0), jours (lun, mer, ven)
    TF->>TF: generateCronExpression()
    TF-->>TF: cron_expression = "0 9 * * 1,3,5"
    U->>TF: Sélectionne agent + input_text
    U->>TF: Configure output_type = "email"
    U->>TF: Configure email_to + email_subject
    U->>TF: Clic "Sauvegarder"
    TF->>API: POST /api/triggers
    API->>CRUD: create_trigger(trigger_data, user_id)
    CRUD->>DB: INSERT INTO triggers
    DB-->>CRUD: Trigger créé
    CRUD-->>API: Trigger
    API-->>F: Trigger créé
    
    Note over SCH,APS: Rechargement automatique (toutes les 5 min)
    APS->>SCH: reload_cron_triggers()
    SCH->>DB: SELECT triggers WHERE type=cron AND enabled=true
    DB-->>SCH: Triggers[]
    
    loop Pour chaque trigger cron
        SCH->>SCH: parse_cron_expression(cron_expression)
        SCH->>APS: add_job(execute_trigger_with_config, trigger="cron", ...)
        APS-->>SCH: Job ajouté
    end
    
    Note over APS: Job programmé pour exécution future
    APS->>APS: Attend déclenchement selon cron expression
```

---

## 📊 Diagrammes d'activité

### Activité : Workflow de traitement d'un nœud

```mermaid
flowchart TD
    Start([Création nœud]) --> Inbox[Status: inbox]
    Inbox --> IA{Agent IA<br/>analyse}
    IA -->|Génère proposition| Proposal[Proposal créé<br/>status: pending]
    Proposal --> User{Utilisateur<br/>consulte}
    User -->|Valide| Apply[Appliquer structuration]
    User -->|Modifie| Modify[Modifier puis appliquer]
    User -->|Rejette| Reject[Rejeter proposition]
    Apply --> Ready[Status: ready]
    Modify --> Ready
    Reject --> Inbox
    Ready --> Doing[Status: doing]
    Doing --> Waiting{En attente<br/>dépendance?}
    Waiting -->|Oui| Wait[Status: waiting]
    Waiting -->|Non| Done[Status: done]
    Wait --> Ready
    Done --> End([Terminé])
```

---

### Activité : Cycle de vie d'un trigger

```mermaid
flowchart TD
    Start([Création trigger]) --> Created[Trigger créé<br/>enabled: true]
    Created --> Cron{Type?}
    Cron -->|cron| Schedule[Expression cron configurée]
    Cron -->|date_reached| Date[Date/heure configurée]
    Cron -->|email_received| Email[Attente email]
    Cron -->|manual| Manual[Manuel uniquement]
    
    Schedule --> Scheduler[APScheduler charge trigger]
    Date --> Scheduler
    Email --> Scheduler
    
    Scheduler --> Wait[Attente déclenchement]
    Wait --> Triggered{Trigger<br/>déclenché?}
    Triggered -->|Oui| Execute[Exécution task]
    Triggered -->|Non| Wait
    
    Execute --> Task{task_type?}
    Task -->|agent| Agent[Exécute agent IA]
    Task -->|action| Action[Exécute action]
    
    Agent --> Result[Résultat obtenu]
    Action --> Result
    
    Result --> Output{output_type?}
    Output -->|screen| Log[Log résultat]
    Output -->|email| Send[Envoie email]
    
    Log --> Update[UPDATE last_fired_at]
    Send --> Update
    
    Update --> Disable{Type<br/>date_reached?}
    Disable -->|Oui| Disabled[Trigger désactivé]
    Disable -->|Non| Wait
    
    Disabled --> End([Terminé])
    Manual --> End
```

---

## 🔗 Relations entre diagrammes

Ces diagrammes complètent la documentation existante :

- **Diagrammes de classe** : Détails dans [ARCHITECTURE.md](ARCHITECTURE.md#base-de-données)
- **Diagrammes de séquence** : Flux détaillés dans [FLUX_MATRICE.md](FLUX_MATRICE.md#séquences-dexécution)
- **Diagrammes d'activité** : Workflows dans [FUNCTIONAL.md](FUNCTIONAL.md#workflows-métier)

---

## 📝 Utilisation des diagrammes

### Visualisation

Ces diagrammes peuvent être visualisés avec :

1. **Mermaid Live Editor** : [https://mermaid.live/](https://mermaid.live/)
   - Copier-coller le code Mermaid
   - Visualisation interactive

2. **VS Code** : 
   - Extension "Markdown Preview Mermaid Support"
   - Prévisualisation intégrée

3. **GitHub/GitLab** : 
   - Rendu automatique dans les fichiers `.md`
   - Pas d'extension nécessaire

4. **Documentation générée** :
   - Intégration possible avec MkDocs, Docusaurus, etc.
   - Plugins Mermaid disponibles

### Export

Pour exporter en image :

```bash
# Avec Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagramme.mmd -o diagramme.png

# Avec Mermaid Live Editor
# Utiliser l'option "Export" dans l'interface
```

---

## 🎨 Diagrammes supplémentaires

### Diagramme de composants Frontend

```mermaid
classDiagram
    class App {
        +Routes
        +ThemeProvider
        +AuthProvider
    }

    class Dashboard {
        +isDrawerOpen
        +activeView
        +toggleDrawer()
    }

    class MindmapCanvas {
        +nodes
        +edges
        +selectedNode
        +onNodeClick()
        +onNodeDragStop()
    }

    class NodeDetails {
        +node
        +triggers
        +onUpdate()
        +handleAddTrigger()
        +handleExecuteTrigger()
    }

    class TriggerForm {
        +trigger
        +onSave()
        +generateCronExpression()
    }

    class AuthProvider {
        +isAuthenticated
        +user
        +login()
        +logout()
    }

    class AuthStore {
        +isAuthenticated
        +user
        +tokens
        +setAuth()
        +clearAuth()
    }

    class MindmapStore {
        +nodes
        +edges
        +selectedNode
        +setSelectedNode()
        +updateNode()
    }

    App --> Dashboard
    App --> AuthProvider
    Dashboard --> MindmapCanvas
    Dashboard --> NodeDetails
    NodeDetails --> TriggerForm
    AuthProvider --> AuthStore
    MindmapCanvas --> MindmapStore
    NodeDetails --> MindmapStore
```

---

### Diagramme d'état : Cycle de vie d'un nœud

```mermaid
stateDiagram-v2
    [*] --> inbox: Création
    inbox --> clarify: Nécessite clarification
    inbox --> ready: Structuration validée
    clarify --> ready: Clarification terminée
    ready --> doing: Démarrage
    doing --> waiting: En attente dépendance
    doing --> done: Terminé
    waiting --> ready: Dépendance résolue
    waiting --> doing: Reprise
    done --> [*]
```

---

### Diagramme d'état : Authentification

```mermaid
stateDiagram-v2
    [*] --> non_authentifie: Initialisation
    non_authentifie --> authentifie: Login réussi
    authentifie --> non_authentifie: Logout
    authentifie --> token_expire: Token expiré
    token_expire --> authentifie: Refresh réussi
    token_expire --> non_authentifie: Refresh échoué
```

---

**Dernière mise à jour** : 2026-01-22
