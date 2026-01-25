# Documentation Fonctionnelle

## Vue d'ensemble métier

**Personal Assistant** est une application d'assistant personnel intelligent qui permet de :
- **Organiser** ses idées, tâches et projets dans un mindmap interactif
- **Automatiser** des actions via des triggers et agents IA
- **Structurer** automatiquement le contenu avec l'intelligence artificielle
- **Recevoir** et traiter des emails automatiquement
- **Planifier** des tâches récurrentes ou ponctuelles

---

## Personas et cas d'usage

### Persona 1 : Professionnel occupé

**Besoin** : Gérer efficacement les informations qui arrivent par email et les transformer en actions.

**Cas d'usage** :
1. Reçoit un email avec une demande
2. L'application crée automatiquement un nœud dans l'inbox
3. L'IA propose une structuration (tâche, idée, note)
4. L'utilisateur valide ou modifie la proposition
5. Le nœud est organisé dans le mindmap

### Persona 2 : Chercheur / Veilleur

**Besoin** : Suivre l'actualité sur un sujet et recevoir des synthèses régulières.

**Cas d'usage** :
1. Configure un agent de veille (ex: "News Monitor Agent")
2. Crée un trigger cron (ex: tous les lundis à 9h)
3. L'agent recherche les actualités sur le sujet
4. Génère un rapport Markdown structuré
5. Envoie le rapport par email automatiquement

### Persona 3 : Gestionnaire de projet

**Besoin** : Organiser des projets complexes avec dépendances et rappels.

**Cas d'usage** :
1. Crée des nœuds "projet" dans le mindmap
2. Ajoute des sous-tâches avec dépendances
3. Configure des triggers pour les dates importantes
4. Reçoit des rappels automatiques
5. Suit l'avancement via les statuts des nœuds

---

## Fonctionnalités principales

### 1. Gestion de mindmap

#### Concept

Un **mindmap** est une représentation visuelle hiérarchique d'informations. Dans Personal Assistant :
- Les **nœuds** représentent des idées, tâches, notes, projets ou événements
- Les **arêtes** (edges) représentent les relations entre nœuds
- L'organisation est **dynamique** et peut être restructurée par l'IA

#### Types de nœuds

| Type | Description | Usage |
|------|-------------|-------|
| **idea** | Idée, concept | Capturer des idées à développer |
| **task** | Tâche à faire | Actions concrètes à réaliser |
| **note** | Note, information | Documentation, références |
| **project** | Projet | Regroupement de tâches |
| **event** | Événement | Dates, rendez-vous |

#### Statuts des nœuds

**Workflow de traitement** :

```
inbox → clarify → ready → doing → waiting → done
  ↓        ↓        ↓       ↓        ↓
  └────────┴────────┴───────┴────────┘
         Gestion manuelle
```

- **`inbox`** : Nouveau, non traité
- **`clarify`** : Nécessite clarification
- **`ready`** : Prêt à être traité
- **`doing`** : En cours
- **`waiting`** : En attente (dépendance)
- **`done`** : Terminé

#### Relations entre nœuds

| Relation | Description | Usage |
|----------|-------------|-------|
| **related** | Lié, connexe | Nœuds sur le même sujet |
| **parent** | Parent-enfant | Hiérarchie |
| **depends_on** | Dépendance | Tâche B dépend de A |
| **mentions** | Mention | Référence à un autre nœud |
| **reference** | Référence | Lien vers documentation |

#### Fonctionnalités

- **Création** : Saisie de texte libre → création de nœud
- **Édition** : Modification du label, description, tags
- **Déplacement** : Drag & drop dans le canvas
- **Structuration IA** : L'IA propose automatiquement :
  - Type de nœud
  - Tags
  - Relations avec autres nœuds
  - Position dans la hiérarchie
- **Recherche** : Filtrage par tags, type, statut

---

### 2. Agents IA configurables

#### Concept

Un **agent IA configurable** est un assistant spécialisé qui peut être personnalisé pour des tâches spécifiques. Chaque agent :
- A un **persona** (rôle, comportement)
- Reçoit des **instructions** détaillées
- Utilise des **outils** (recherche web, etc.)
- Produit une **sortie structurée** en Markdown

#### Exemples d'agents

**1. News Monitor Agent** (Agent de veille)
- **Persona** : Journaliste spécialisé en veille informationnelle
- **Mission** : Effectuer une veille sur un thème donné
- **Outils** : `web_search`, `web_search_news`
- **Sortie** : Rapport Markdown avec :
  - Résumé exécutif
  - Découvertes clés
  - Tendances
  - Sources
  - Recommandations

**2. Architect Agent** (Agent architecte)
- **Persona** : Architecte logiciel
- **Mission** : Analyser et structurer des besoins techniques
- **Sortie** : Architecture proposée, composants, dépendances

#### Configuration d'un agent

**Format Markdown avec YAML frontmatter** :

```markdown
---
name: "News Monitor Agent"
slug: "news-monitor"
description: "Agent de veille informationnelle"
tools: ["web_search", "web_search_news"]
output_schema:
  type: object
  properties:
    executive_summary:
      type: string
    key_findings:
      type: array
      items:
        type: object
        properties:
          title: { type: string }
          importance: { type: string, enum: ["high", "medium", "low"] }
---

## Persona
Journaliste spécialisé en veille informationnelle...

## Instructions
1. Recherche d'informations...
2. Analyse et synthèse...
3. Structuration du rapport...
```

#### Exécution d'un agent

**Flux** :
1. L'utilisateur sélectionne un agent
2. Saisit un texte d'entrée (requête, thème, etc.)
3. L'agent :
   - Utilise les outils nécessaires (recherche web, etc.)
   - Consulte le LLM (OpenAI) avec le prompt configuré
   - Génère une réponse en Markdown
4. La sortie est parsée selon le schéma
5. Affichage formaté dans l'interface

**Résultats** :
- **Sortie brute** : Markdown complet
- **Sortie parsée** : Structure JSON selon schéma
- **Temps d'exécution** : Mesuré et loggé
- **Prompt utilisé** : Conservé pour traçabilité

---

### 3. Système de triggers et actions

#### Concept

Un **trigger** (déclencheur) est un événement qui lance automatiquement une ou plusieurs **actions**.

**Exemple** : "Tous les lundis à 9h, exécuter l'agent de veille et m'envoyer le résultat par email"

#### Types de triggers

| Type | Déclenchement | Usage |
|------|---------------|-------|
| **email_received** | Réception d'un email | Traitement automatique d'emails |
| **date_reached** | Date/heure précise | Rappels, tâches ponctuelles |
| **cron** | Expression cron | Tâches récurrentes (quotidien, hebdo, etc.) |
| **state_changed** | Changement de statut d'un nœud | Workflow automatique |
| **manual** | Déclenchement manuel | Tests, exécution à la demande |

#### Configuration d'un trigger cron

**Interface utilisateur** :
- Sélection de l'heure (ex: 9h00)
- Sélection des jours (ex: Lundi, Mercredi, Vendredi)
- Génération automatique de l'expression cron : `0 9 * * 1,3,5`

**Expression cron** :
```
minute heure jour_mois mois jour_semaine
0       9    *         *    1,3,5
```

#### Actions disponibles

| Action | Description | Configuration |
|--------|-------------|---------------|
| **send_email** | Envoyer un email | `to`, `subject`, `body` |
| **draft_email** | Créer un brouillon | Contenu du brouillon |
| **call_api** | Appeler une API | URL, méthode, headers, body |
| **update_node** | Modifier un nœud | Champs à modifier |
| **run_agent** | Exécuter un agent IA | Agent ID, input_text |
| **notify** | Notification | Message |
| **create_reminder** | Créer un rappel | Date, message |

#### Configuration d'un trigger

**Éléments configurables** :
- **Type de trigger** : cron, date_reached, etc.
- **Tâche à exécuter** :
  - Type : Agent IA ou Action
  - Sélection : Agent configurable ou Action spécifique
- **Texte d'entrée** : Input pour l'agent (optionnel)
- **Type de rendu** :
  - `screen` : Affichage à l'écran
  - `email` : Envoi par email
- **Configuration email** (si rendu = email) :
  - Destinataire
  - Sujet (optionnel)

#### Exécution d'un trigger

**Flux automatique (cron/date_reached)** :
```
Scheduler détecte trigger échu
    ↓
Lit configuration (task_type, task_id, output_type)
    ↓
Exécute la tâche (agent ou action)
    ↓
Si output_type = "email"
    → Formate le résultat
    → Envoie par SMTP
    → Log "Email envoyé"
Sinon
    → Log l'exécution
```

**Flux manuel** :
- L'utilisateur clique sur "Lancer" dans l'interface
- Même flux que ci-dessus
- Résultat affiché dans une modal

---

### 4. Ingestion et structuration automatique

#### Ingestion de texte

**Sources** :
- **Interface utilisateur** : Saisie manuelle
- **Email** : Réception automatique
- **API** : Intégration externe

**Flux d'ingestion** :
```
Texte saisi → Création nœud (status: inbox)
    ↓
Agent "StructurerMindmap" analyse le texte
    ↓
Génère une proposition (Proposal) :
  - Type suggéré
  - Tags suggérés
  - Relations suggérées
  - Position suggérée
    ↓
Utilisateur valide/modifie/rejette
    ↓
Si validé → Application de la proposition
```

#### Structuration IA

**Agent "StructurerMindmap"** :
- Analyse le texte libre
- Identifie le type (idée, tâche, note, projet, événement)
- Extrait des tags pertinents
- Détecte des relations avec d'autres nœuds existants
- Propose une position dans la hiérarchie

**Proposition (Proposal)** :
```json
{
  "title": "Titre suggéré",
  "type": "task",
  "domain": "Technique",
  "tags": ["urgent", "backend"],
  "links": [
    {
      "toNodeId": "uuid",
      "relationType": "depends_on",
      "confidence": 0.8
    }
  ],
  "placement": {
    "parentNodeId": "uuid",
    "branchLabel": "Projets"
  },
  "nextAction": "Contacter l'équipe",
  "confidence": 0.85,
  "rationale": ["Le texte mentionne une dépendance..."]
}
```

**Workflow de validation** :
1. Proposition créée automatiquement
2. Affichage dans l'interface
3. Utilisateur peut :
   - **Approuver** : Application immédiate
   - **Modifier** : Ajuster puis appliquer
   - **Rejeter** : Ignorer la proposition

---

### 5. Gestion des emails

#### Réception automatique

**Fonctionnement** :
- Polling IMAP toutes les 2 minutes
- Récupération des emails non lus
- Pour chaque email :
  1. Création d'un nœud dans l'inbox
  2. Source : `NodeSource.email`
  3. Contenu : Snippet de l'email (500 premiers caractères)
  4. Métadonnées : Expéditeur, sujet, date
  5. Génération d'une proposition de structuration
  6. Marquage comme traité

**Déduplication** :
- Utilisation du `Message-ID` comme clé d'idempotence
- Évite les doublons en cas de re-polling

#### Envoi d'emails

**Cas d'usage** :
- Résultats d'agents IA envoyés automatiquement
- Notifications
- Rappels

**Format** :
- Email multipart (text + HTML)
- Conversion Markdown → HTML
- Mise en forme professionnelle

**Configuration** :
- Serveur SMTP configuré dans `.env`
- Support de différents fournisseurs (Gmail, Gandi, etc.)

---

### 6. Recherche web intégrée

#### Fonctionnalités

**Recherche générale** :
- Recherche web sur un sujet donné
- Résultats structurés (titre, URL, snippet, source, date)
- Support Google (SerpAPI) et Bing

**Recherche d'actualités** :
- Actualités récentes (24-48h)
- Filtrage par langue
- Résultats triés par pertinence

#### Utilisation par les agents

Les agents IA peuvent utiliser la recherche web pour :
- Obtenir des informations à jour
- Vérifier des faits
- Trouver des sources
- Analyser des tendances

**Exemple** : L'agent de veille utilise `web_search_news` pour trouver les dernières actualités sur un sujet.

---

## Workflows métier

### Workflow 1 : Traitement d'un email entrant

```
1. Email reçu → Polling IMAP détecte
2. Création nœud dans inbox
3. Agent IA analyse le contenu
4. Proposition générée (type, tags, relations)
5. Utilisateur notifié (optionnel)
6. Utilisateur valide/modifie la proposition
7. Nœud structuré et organisé dans le mindmap
```

### Workflow 2 : Veille informationnelle automatisée

```
1. Utilisateur configure :
   - Agent : "News Monitor Agent"
   - Trigger : Cron (tous les lundis à 9h)
   - Input : "Actualités IA Agentique"
   - Output : Email
2. Chaque lundi à 9h :
   - Trigger déclenché automatiquement
   - Agent exécuté avec l'input
   - Recherche web effectuée
   - Rapport Markdown généré
   - Email envoyé avec le rapport
3. Utilisateur reçoit le rapport dans sa boîte mail
```

### Workflow 3 : Gestion de projet avec dépendances

```
1. Création nœud "Projet X" (type: project)
2. Ajout de sous-tâches (type: task)
3. Définition de dépendances (edge: depends_on)
4. Configuration de triggers pour dates importantes
5. Suivi de l'avancement via statuts :
   - ready → doing → done
6. Notifications automatiques pour dépendances bloquantes
```

### Workflow 4 : Structuration manuelle avec aide IA

```
1. Utilisateur saisit du texte libre
2. Clic sur "Structurer"
3. Agent IA analyse et propose :
   - Type de nœud
   - Tags
   - Relations
   - Position
4. Utilisateur révise la proposition
5. Application de la structure
6. Nœud organisé dans le mindmap
```

---

## Règles métier

### Règles de gestion des nœuds

1. **Unicité** : Chaque nœud a un UUID unique
2. **Source** : Chaque nœud a une source (ui, email, api)
3. **Statut initial** : Nouveau nœud → `inbox`
4. **Tags** : Liste de chaînes, non vide par défaut
5. **Position** : Coordonnées {x, y} dans le canvas

### Règles de gestion des triggers

1. **Un trigger doit être associé à un nœud**
2. **Un trigger désactivé ne s'exécute pas**
3. **Les triggers cron sont rechargés toutes les 5 minutes**
4. **Un trigger peut avoir plusieurs actions** (ordre d'exécution)
5. **Déduplication** : `dedupe_key` pour éviter les exécutions multiples

### Règles de gestion des agents

1. **Un agent doit avoir un schéma de sortie défini**
2. **Les outils doivent être disponibles** (sinon erreur)
3. **La sortie doit respecter le schéma** (sinon parsing échoue)
4. **Chaque exécution est loggée** (traçabilité)

### Règles de gestion des emails

1. **Un email traité ne crée pas de nouveau nœud** (idempotence)
2. **Seuls les emails non lus sont traités**
3. **Le snippet est limité à 500 caractères**
4. **Les métadonnées sont conservées** dans `source_ref`

---

## Contraintes et limites

### Contraintes techniques

- **Base de données** : PostgreSQL requis
- **API externe** : OpenAI API pour les agents IA
- **Email** : Serveur IMAP/SMTP configuré
- **Recherche web** : API Google ou Bing (optionnel)

### Limites fonctionnelles

- **Agents** : Dépendent de la disponibilité de l'API OpenAI
- **Recherche web** : Limite de résultats (10 pour Google, 50 pour Bing)
- **Emails** : Polling toutes les 2 minutes (pas en temps réel)
- **Triggers cron** : Rechargement toutes les 5 minutes (pas instantané)

### Contraintes de sécurité

- **Authentification** : Requise pour toutes les opérations
- **Tokens** : Expiration après 24h (configurable)
- **CORS** : Origines limitées (configurées)
- **Mots de passe** : Minimum de complexité (à implémenter)

---

## Métriques et indicateurs

### Métriques utilisateur

- **Nombre de nœuds créés** : Productivité
- **Taux de validation des propositions** : Efficacité de l'IA
- **Nombre de triggers actifs** : Niveau d'automatisation
- **Temps moyen de traitement** : Performance

### Métriques système

- **Temps d'exécution des agents** : Performance IA
- **Taux de succès des triggers** : Fiabilité
- **Nombre d'emails traités** : Volume
- **Erreurs d'exécution** : Stabilité

---

## Évolutions fonctionnelles prévues

### Court terme

- **Notifications en temps réel** : WebSockets
- **Filtres avancés** : Recherche dans les nœuds
- **Export/Import** : Sauvegarde de mindmaps
- **Collaboration** : Partage de mindmaps

### Moyen terme

- **Templates d'agents** : Bibliothèque d'agents pré-configurés
- **Workflows visuels** : Éditeur de workflows
- **Intégrations** : Calendrier, Trello, Slack, etc.
- **Mobile** : Application mobile native

### Long terme

- **Multi-utilisateurs** : Collaboration en temps réel
- **IA avancée** : Agents conversationnels
- **Analytics** : Tableaux de bord d'analyse
- **Marketplace** : Partage d'agents entre utilisateurs

---

## Glossaire

| Terme | Définition |
|-------|-----------|
| **Agent IA** | Assistant intelligent configurable pour une tâche spécifique |
| **Action** | Opération automatisée déclenchée par un trigger |
| **Cron** | Expression de planification (ex: `0 9 * * 1,3,5` = lundi, mercredi, vendredi à 9h) |
| **Edge** | Relation entre deux nœuds dans le mindmap |
| **Idempotence** | Propriété garantissant qu'une opération peut être répétée sans effet secondaire |
| **Mindmap** | Représentation visuelle hiérarchique d'informations |
| **Node** | Élément du mindmap (idée, tâche, note, projet, événement) |
| **Proposal** | Proposition de structuration générée par l'IA |
| **Trigger** | Déclencheur qui lance automatiquement des actions |
| **Workflow** | Série d'étapes automatisées pour accomplir une tâche |

---

## Conclusion

**Personal Assistant** est une application complète qui combine :
- **Organisation visuelle** (mindmap)
- **Intelligence artificielle** (agents configurables)
- **Automatisation** (triggers et actions)
- **Intégration email** (réception et envoi)

L'application répond aux besoins de professionnels qui souhaitent :
- Gérer efficacement leurs informations
- Automatiser des tâches répétitives
- Bénéficier de l'aide de l'IA pour structurer et organiser
- Recevoir des synthèses et rapports automatiques

Le système est conçu pour être **extensible** et **personnalisable**, permettant à chaque utilisateur d'adapter l'application à ses besoins spécifiques.
