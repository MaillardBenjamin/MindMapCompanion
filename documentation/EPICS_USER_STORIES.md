# EPICS et User Stories

Document de référence pour la gestion produit de Personal Assistant, structuré en EPICS et User Stories selon les standards Agile/Scrum.

---

## 📋 Glossaire

- **EPIC** : Grande fonctionnalité ou objectif métier qui nécessite plusieurs sprints pour être complété
- **User Story (US)** : Description d'une fonctionnalité du point de vue de l'utilisateur final
- **Acceptance Criteria (AC)** : Critères d'acceptation permettant de valider qu'une US est terminée
- **Definition of Done (DoD)** : Critères généraux pour considérer une US comme terminée

---

## 🎯 EPICS

### EPIC 1 : Gestion de Mindmap
**Description** : Permettre aux utilisateurs de créer, organiser et visualiser leurs idées, tâches et projets dans un mindmap interactif.

**Valeur métier** : Organisation visuelle et hiérarchique de l'information pour améliorer la productivité.

**Priorité** : 🔴 Haute

---

### EPIC 2 : Agents IA Configurables
**Description** : Permettre aux utilisateurs de créer et utiliser des agents IA spécialisés pour automatiser des tâches complexes.

**Valeur métier** : Automatisation intelligente de tâches répétitives ou complexes (veille, analyse, structuration).

**Priorité** : 🔴 Haute

---

### EPIC 3 : Automatisation via Triggers et Actions
**Description** : Permettre aux utilisateurs de configurer des automatisations déclenchées par des événements (cron, email, changement d'état).

**Valeur métier** : Automatisation complète de workflows pour réduire la charge cognitive et augmenter l'efficacité.

**Priorité** : 🔴 Haute

---

### EPIC 4 : Intégration Email
**Description** : Permettre la réception automatique d'emails et leur transformation en nœuds, ainsi que l'envoi de résultats par email.

**Valeur métier** : Intégration avec le canal de communication principal pour capturer et diffuser l'information.

**Priorité** : 🟡 Moyenne

---

### EPIC 5 : Structuration Automatique par IA
**Description** : Utiliser l'IA pour analyser et structurer automatiquement le contenu saisi (type, tags, relations, position).

**Valeur métier** : Réduction du temps de saisie et amélioration de la qualité de l'organisation.

**Priorité** : 🟡 Moyenne

---

### EPIC 6 : Recherche Web Intégrée
**Description** : Permettre aux agents IA d'effectuer des recherches web pour obtenir des informations à jour.

**Valeur métier** : Enrichissement des réponses des agents avec des données actualisées.

**Priorité** : 🟢 Basse

---

## 📝 User Stories

### EPIC 1 : Gestion de Mindmap

#### US-1.1 : Créer un nœud dans le mindmap
**En tant que** utilisateur,  
**Je veux** créer un nouveau nœud en saisissant du texte libre,  
**Afin de** capturer rapidement mes idées, tâches ou notes sans avoir à remplir un formulaire complexe.

**Critères d'acceptation** :
- [ ] Je peux saisir du texte libre dans un champ de saisie
- [ ] Le nœud est créé avec le statut "inbox" par défaut
- [ ] Le nœud apparaît immédiatement dans le mindmap
- [ ] Je peux voir le nœud créé avec son texte brut
- [ ] Le nœud a une position par défaut dans le canvas

**Priorité** : 🔴 Haute  
**Story Points** : 3  
**Sprint** : 1

---

#### US-1.2 : Modifier un nœud existant
**En tant que** utilisateur,  
**Je veux** modifier le contenu, le type, les tags ou le statut d'un nœud,  
**Afin de** mettre à jour mes informations et organiser mon mindmap.

**Critères d'acceptation** :
- [ ] Je peux éditer le titre/description d'un nœud
- [ ] Je peux changer le type (idée, tâche, note, projet, événement)
- [ ] Je peux ajouter/supprimer des tags
- [ ] Je peux changer le statut (inbox → ready → doing → done)
- [ ] Les modifications sont sauvegardées automatiquement
- [ ] Je peux annuler mes modifications

**Priorité** : 🔴 Haute  
**Story Points** : 5  
**Sprint** : 1

---

#### US-1.3 : Déplacer un nœud dans le mindmap
**En tant que** utilisateur,  
**Je veux** déplacer un nœud par drag & drop dans le canvas,  
**Afin de** réorganiser visuellement mon mindmap selon mes besoins.

**Critères d'acceptation** :
- [ ] Je peux cliquer-glisser un nœud pour le déplacer
- [ ] La position est sauvegardée automatiquement
- [ ] Le nœud reste visible pendant le déplacement
- [ ] Je peux voir un feedback visuel pendant le drag
- [ ] La position est persistée après rechargement de la page

**Priorité** : 🟡 Moyenne  
**Story Points** : 5  
**Sprint** : 2

---

#### US-1.4 : Créer une relation entre deux nœuds
**En tant que** utilisateur,  
**Je veux** créer une relation (parent, dépendance, référence) entre deux nœuds,  
**Afin de** représenter les liens logiques entre mes idées et tâches.

**Critères d'acceptation** :
- [ ] Je peux sélectionner deux nœuds pour créer une relation
- [ ] Je peux choisir le type de relation (parent, dépendance, référence, etc.)
- [ ] La relation est visualisée par une arête dans le mindmap
- [ ] Je peux voir les relations existantes
- [ ] Je peux supprimer une relation

**Priorité** : 🟡 Moyenne  
**Story Points** : 8  
**Sprint** : 2

---

#### US-1.5 : Filtrer et rechercher dans le mindmap
**En tant que** utilisateur,  
**Je veux** filtrer les nœuds par type, statut ou tags, et rechercher par texte,  
**Afin de** trouver rapidement l'information dont j'ai besoin dans un mindmap volumineux.

**Critères d'acceptation** :
- [ ] Je peux filtrer par type de nœud
- [ ] Je peux filtrer par statut
- [ ] Je peux filtrer par tags
- [ ] Je peux rechercher par texte dans le contenu des nœuds
- [ ] Les résultats sont mis en évidence visuellement
- [ ] Je peux combiner plusieurs filtres

**Priorité** : 🟢 Basse  
**Story Points** : 5  
**Sprint** : 3

---

### EPIC 2 : Agents IA Configurables

#### US-2.1 : Créer un agent IA configurable
**En tant que** utilisateur,  
**Je veux** créer un agent IA en définissant son persona, ses instructions et son schéma de sortie,  
**Afin de** avoir un assistant spécialisé pour des tâches spécifiques (veille, analyse, etc.).

**Critères d'acceptation** :
- [ ] Je peux créer un agent via un fichier Markdown
- [ ] Je peux définir un persona (rôle de l'agent)
- [ ] Je peux définir des instructions détaillées
- [ ] Je peux définir un schéma de sortie JSON
- [ ] Je peux sélectionner les outils disponibles (web_search, etc.)
- [ ] L'agent est sauvegardé et réutilisable

**Priorité** : 🔴 Haute  
**Story Points** : 8  
**Sprint** : 1

---

#### US-2.2 : Exécuter un agent IA manuellement
**En tant que** utilisateur,  
**Je veux** exécuter un agent IA avec un texte d'entrée,  
**Afin de** obtenir une réponse structurée pour une tâche spécifique.

**Critères d'acceptation** :
- [ ] Je peux sélectionner un agent dans une liste
- [ ] Je peux saisir un texte d'entrée
- [ ] L'agent s'exécute et utilise les outils configurés (recherche web, etc.)
- [ ] Je vois la progression de l'exécution
- [ ] Je reçois une sortie formatée en Markdown
- [ ] Je peux voir le temps d'exécution
- [ ] Je peux voir le prompt utilisé (pour debug)

**Priorité** : 🔴 Haute  
**Story Points** : 8  
**Sprint** : 1

---

#### US-2.3 : Voir l'historique des exécutions d'agents
**En tant que** utilisateur,  
**Je veux** consulter l'historique des exécutions d'un agent,  
**Afin de** suivre les résultats passés et améliorer mes prompts.

**Critères d'acceptation** :
- [ ] Je peux voir la liste des exécutions d'un agent
- [ ] Pour chaque exécution, je vois : date, input, output, temps d'exécution
- [ ] Je peux filtrer par date ou agent
- [ ] Je peux consulter les détails d'une exécution
- [ ] Je peux exporter l'historique

**Priorité** : 🟢 Basse  
**Story Points** : 5  
**Sprint** : 3

---

#### US-2.4 : Charger des agents depuis des fichiers
**En tant que** utilisateur administrateur,  
**Je veux** charger des agents pré-configurés depuis des fichiers Markdown,  
**Afin de** disposer rapidement d'agents spécialisés sans les créer manuellement.

**Critères d'acceptation** :
- [ ] Je peux charger un fichier .md contenant la config d'un agent
- [ ] Le parser valide le format (frontmatter YAML + sections Markdown)
- [ ] L'agent est créé automatiquement dans la base de données
- [ ] Je reçois un message de confirmation ou d'erreur
- [ ] Je peux charger plusieurs agents en une fois

**Priorité** : 🟡 Moyenne  
**Story Points** : 5  
**Sprint** : 2

---

### EPIC 3 : Automatisation via Triggers et Actions

#### US-3.1 : Créer un trigger cron (planifié)
**En tant que** utilisateur,  
**Je veux** créer un trigger qui s'exécute automatiquement selon un planning (ex: tous les lundis à 9h),  
**Afin de** automatiser des tâches récurrentes sans intervention manuelle.

**Critères d'acceptation** :
- [ ] Je peux créer un trigger de type "cron"
- [ ] Je peux sélectionner l'heure (0-23)
- [ ] Je peux sélectionner la minute (0-59)
- [ ] Je peux sélectionner les jours de la semaine (lundi, mercredi, etc.)
- [ ] L'expression cron est générée automatiquement
- [ ] Je peux aussi saisir manuellement une expression cron
- [ ] Le trigger est activé par défaut

**Priorité** : 🔴 Haute  
**Story Points** : 8  
**Sprint** : 1

---

#### US-3.2 : Configurer une tâche à exécuter (agent ou action)
**En tant que** utilisateur,  
**Je veux** associer un agent IA ou une action à un trigger,  
**Afin de** définir ce qui sera exécuté automatiquement.

**Critères d'acceptation** :
- [ ] Je peux choisir entre "agent" ou "action"
- [ ] Si agent : je peux sélectionner un agent dans la liste
- [ ] Si action : je peux sélectionner une action dans la liste
- [ ] Je peux définir un texte d'entrée pour l'agent
- [ ] La configuration est sauvegardée dans le trigger

**Priorité** : 🔴 Haute  
**Story Points** : 5  
**Sprint** : 1

---

#### US-3.3 : Configurer le type de rendu (écran ou email)
**En tant que** utilisateur,  
**Je veux** choisir si le résultat d'un trigger est affiché à l'écran ou envoyé par email,  
**Afin de** recevoir les résultats automatiquement dans ma boîte mail.

**Critères d'acceptation** :
- [ ] Je peux choisir "screen" (affichage) ou "email" (envoi)
- [ ] Si email : je peux définir le destinataire
- [ ] Si email : je peux définir le sujet (optionnel)
- [ ] Si email : le résultat est formaté en HTML
- [ ] Si screen : le résultat est affiché dans une modal

**Priorité** : 🔴 Haute  
**Story Points** : 5  
**Sprint** : 1

---

#### US-3.4 : Exécuter un trigger manuellement
**En tant que** utilisateur,  
**Je veux** exécuter un trigger manuellement pour tester ou déclencher immédiatement,  
**Afin de** vérifier que ma configuration fonctionne avant de l'activer automatiquement.

**Critères d'acceptation** :
- [ ] Je peux cliquer sur "Lancer" pour un trigger
- [ ] Je peux surcharger le texte d'entrée si c'est un agent
- [ ] Je peux choisir le type de rendu (screen/email) pour cette exécution
- [ ] Je vois le résultat de l'exécution
- [ ] Si email : je reçois un message de confirmation
- [ ] Si screen : le résultat s'affiche dans une modal

**Priorité** : 🔴 Haute  
**Story Points** : 5  
**Sprint** : 1

---

#### US-3.5 : Créer un trigger pour date/heure précise
**En tant que** utilisateur,  
**Je veux** créer un trigger qui s'exécute à une date et heure précises,  
**Afin de** planifier des tâches ponctuelles (rappels, rapports, etc.).

**Critères d'acceptation** :
- [ ] Je peux créer un trigger de type "date_reached"
- [ ] Je peux sélectionner une date
- [ ] Je peux sélectionner une heure
- [ ] Le trigger s'exécute automatiquement à la date/heure définie
- [ ] Le trigger est désactivé après exécution (ou marqué comme exécuté)

**Priorité** : 🟡 Moyenne  
**Story Points** : 5  
**Sprint** : 2

---

#### US-3.6 : Créer un trigger déclenché par email
**En tant que** utilisateur,  
**Je veux** créer un trigger qui s'exécute automatiquement à la réception d'un email,  
**Afin de** traiter automatiquement les emails entrants.

**Critères d'acceptation** :
- [ ] Je peux créer un trigger de type "email_received"
- [ ] Le trigger s'exécute automatiquement quand un email arrive
- [ ] Je peux filtrer par expéditeur ou sujet (optionnel)
- [ ] Le contenu de l'email est utilisé comme input pour l'agent/action

**Priorité** : 🟡 Moyenne  
**Story Points** : 8  
**Sprint** : 2

---

#### US-3.7 : Activer/désactiver un trigger
**En tant que** utilisateur,  
**Je veux** activer ou désactiver un trigger sans le supprimer,  
**Afin de** mettre en pause des automatisations temporairement.

**Critères d'acceptation** :
- [ ] Je peux activer/désactiver un trigger via un switch
- [ ] Un trigger désactivé ne s'exécute pas
- [ ] L'état est sauvegardé immédiatement
- [ ] Je peux voir visuellement si un trigger est actif ou non

**Priorité** : 🟡 Moyenne  
**Story Points** : 2  
**Sprint** : 2

---

#### US-3.8 : Voir l'historique d'exécution d'un trigger
**En tant que** utilisateur,  
**Je veux** voir quand et comment un trigger a été exécuté,  
**Afin de** suivre l'activité de mes automatisations et diagnostiquer les problèmes.

**Critères d'acceptation** :
- [ ] Je peux voir la date/heure de la dernière exécution
- [ ] Je peux voir l'historique des exécutions
- [ ] Pour chaque exécution, je vois : succès/échec, résultat, durée
- [ ] Je peux consulter les logs détaillés

**Priorité** : 🟢 Basse  
**Story Points** : 5  
**Sprint** : 3

---

### EPIC 4 : Intégration Email

#### US-4.1 : Recevoir des emails automatiquement
**En tant que** utilisateur,  
**Je veux** que les emails reçus soient automatiquement transformés en nœuds dans l'inbox,  
**Afin de** capturer l'information sans intervention manuelle.

**Critères d'acceptation** :
- [ ] Les emails sont récupérés automatiquement via IMAP (toutes les 2 minutes)
- [ ] Chaque email crée un nœud dans l'inbox
- [ ] Le nœud contient le snippet de l'email (500 premiers caractères)
- [ ] Les métadonnées (expéditeur, sujet, date) sont conservées
- [ ] Les emails déjà traités ne créent pas de doublons (idempotence)

**Priorité** : 🟡 Moyenne  
**Story Points** : 8  
**Sprint** : 1

---

#### US-4.2 : Recevoir les résultats d'agents par email
**En tant que** utilisateur,  
**Je veux** recevoir les résultats d'exécution d'agents par email,  
**Afin de** consulter les résultats même si je ne suis pas connecté à l'application.

**Critères d'acceptation** :
- [ ] Je peux configurer un trigger pour envoyer les résultats par email
- [ ] L'email contient le résultat formaté en HTML
- [ ] Le Markdown est converti en HTML lisible
- [ ] Le sujet de l'email est personnalisable
- [ ] Je reçois l'email dans ma boîte mail

**Priorité** : 🔴 Haute  
**Story Points** : 5  
**Sprint** : 1

---

#### US-4.3 : Configurer la connexion IMAP
**En tant que** administrateur,  
**Je veux** configurer les paramètres de connexion IMAP (serveur, port, credentials),  
**Afin de** connecter l'application à ma boîte mail.

**Critères d'acceptation** :
- [ ] Je peux configurer le serveur IMAP
- [ ] Je peux configurer le port (993 pour SSL)
- [ ] Je peux configurer les credentials (user, password)
- [ ] Je peux tester la connexion
- [ ] La configuration est sécurisée (variables d'environnement)

**Priorité** : 🟡 Moyenne  
**Story Points** : 3  
**Sprint** : 1

---

### EPIC 5 : Structuration Automatique par IA

#### US-5.1 : Proposer une structuration automatique
**En tant que** utilisateur,  
**Je veux** que l'IA analyse un texte et propose automatiquement un type, des tags et des relations,  
**Afin de** gagner du temps et améliorer la qualité de l'organisation.

**Critères d'acceptation** :
- [ ] Quand je crée un nœud, une proposition de structuration est générée automatiquement
- [ ] La proposition inclut : type suggéré, tags suggérés, relations suggérées
- [ ] La proposition inclut un niveau de confiance
- [ ] Je peux voir la proposition dans l'interface
- [ ] La proposition est générée rapidement (< 5 secondes)

**Priorité** : 🟡 Moyenne  
**Story Points** : 8  
**Sprint** : 1

---

#### US-5.2 : Valider ou modifier une proposition de structuration
**En tant que** utilisateur,  
**Je veux** approuver, modifier ou rejeter une proposition de structuration,  
**Afin de** garder le contrôle sur l'organisation de mon mindmap.

**Critères d'acceptation** :
- [ ] Je peux approuver une proposition en un clic
- [ ] Je peux modifier la proposition avant de l'appliquer
- [ ] Je peux rejeter la proposition
- [ ] Si j'approuve, la structuration est appliquée immédiatement
- [ ] Si je modifie, je peux ajuster chaque élément (type, tags, relations)

**Priorité** : 🟡 Moyenne  
**Story Points** : 5  
**Sprint** : 1

---

#### US-5.3 : Structurer manuellement avec aide IA
**En tant que** utilisateur,  
**Je veux** demander explicitement une structuration IA sur un nœud existant,  
**Afin de** réorganiser des nœuds créés manuellement.

**Critères d'acceptation** :
- [ ] Je peux cliquer sur "Structurer" pour un nœud
- [ ] Une proposition est générée
- [ ] Je peux valider/modifier/rejeter comme pour les propositions automatiques

**Priorité** : 🟢 Basse  
**Story Points** : 3  
**Sprint** : 2

---

### EPIC 6 : Recherche Web Intégrée

#### US-6.1 : Utiliser la recherche web dans un agent
**En tant que** utilisateur,  
**Je veux** que mes agents IA puissent effectuer des recherches web,  
**Afin de** obtenir des informations à jour pour leurs réponses.

**Critères d'acceptation** :
- [ ] Je peux configurer un agent avec l'outil "web_search"
- [ ] L'agent utilise automatiquement la recherche web quand nécessaire
- [ ] Les résultats de recherche sont intégrés dans la réponse
- [ ] Les sources sont citées dans la réponse

**Priorité** : 🟢 Basse  
**Story Points** : 5  
**Sprint** : 2

---

#### US-6.2 : Rechercher des actualités récentes
**En tant que** utilisateur,  
**Je veux** que mes agents puissent rechercher des actualités récentes (24-48h),  
**Afin de** effectuer une veille informationnelle à jour.

**Critères d'acceptation** :
- [ ] Je peux configurer un agent avec l'outil "web_search_news"
- [ ] L'agent recherche des actualités récentes
- [ ] Les résultats sont triés par pertinence et date
- [ ] Les sources sont fiables et variées

**Priorité** : 🟢 Basse  
**Story Points** : 5  
**Sprint** : 2

---

## 📊 Backlog Priorisé

### Sprint 1 (MVP Core)
- US-1.1 : Créer un nœud dans le mindmap
- US-1.2 : Modifier un nœud existant
- US-2.1 : Créer un agent IA configurable
- US-2.2 : Exécuter un agent IA manuellement
- US-3.1 : Créer un trigger cron (planifié)
- US-3.2 : Configurer une tâche à exécuter (agent ou action)
- US-3.3 : Configurer le type de rendu (écran ou email)
- US-3.4 : Exécuter un trigger manuellement
- US-4.2 : Recevoir les résultats d'agents par email
- US-4.1 : Recevoir des emails automatiquement
- US-5.1 : Proposer une structuration automatique
- US-5.2 : Valider ou modifier une proposition de structuration

**Total Story Points Sprint 1** : 69

### Sprint 2 (Améliorations)
- US-1.3 : Déplacer un nœud dans le mindmap
- US-1.4 : Créer une relation entre deux nœuds
- US-2.4 : Charger des agents depuis des fichiers
- US-3.5 : Créer un trigger pour date/heure précise
- US-3.6 : Créer un trigger déclenché par email
- US-3.7 : Activer/désactiver un trigger
- US-5.3 : Structurer manuellement avec aide IA
- US-6.1 : Utiliser la recherche web dans un agent
- US-6.2 : Rechercher des actualités récentes

**Total Story Points Sprint 2** : 44

### Sprint 3 (Polish & Analytics)
- US-1.5 : Filtrer et rechercher dans le mindmap
- US-2.3 : Voir l'historique des exécutions d'agents
- US-3.8 : Voir l'historique d'exécution d'un trigger

**Total Story Points Sprint 3** : 15

---

## ✅ Definition of Done (DoD)

Une User Story est considérée comme terminée quand :

- [ ] Le code est développé et testé
- [ ] Les tests unitaires passent (> 80% de couverture)
- [ ] Les tests d'intégration passent
- [ ] Le code est revu (code review)
- [ ] La documentation est mise à jour
- [ ] Les critères d'acceptation sont validés
- [ ] L'interface utilisateur est fonctionnelle et responsive
- [ ] Les erreurs sont gérées proprement
- [ ] Le code respecte les standards de qualité (linting)
- [ ] La fonctionnalité est déployée en environnement de test
- [ ] La fonctionnalité est validée par le Product Owner

---

## 📈 Métriques de Succès

### Métriques Utilisateur
- **Taux d'adoption** : % d'utilisateurs qui créent au moins un trigger
- **Taux d'utilisation** : Nombre moyen de nœuds créés par utilisateur
- **Taux de validation des propositions IA** : % de propositions approuvées
- **Temps moyen de création d'un nœud** : < 30 secondes

### Métriques Technique
- **Temps de réponse API** : < 200ms (p95)
- **Temps d'exécution d'un agent** : < 60 secondes (p95)
- **Disponibilité** : > 99.5%
- **Taux d'erreur** : < 1%

---

## 🔄 Évolutions Futures (Backlog)

### EPIC 7 : Collaboration
- US-7.1 : Partager un mindmap avec d'autres utilisateurs
- US-7.2 : Commenter sur un nœud
- US-7.3 : Notifications en temps réel

### EPIC 8 : Intégrations Externes
- US-8.1 : Intégration avec Google Calendar
- US-8.2 : Intégration avec Trello
- US-8.3 : Intégration avec Slack

### EPIC 9 : Analytics et Reporting
- US-9.1 : Tableaux de bord d'activité
- US-9.2 : Rapports d'utilisation des agents
- US-9.3 : Statistiques de productivité

---

**Document maintenu par** : Product Owner  
**Dernière mise à jour** : 2026-01-22  
**Version** : 1.0
