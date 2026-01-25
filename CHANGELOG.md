# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]

### À venir
- Fonctionnalités en cours de développement
- Améliorations planifiées

---

## [1.0.0] - 2026-01-22

### Ajouté
- **Authentification JWT** : Système complet d'authentification avec access tokens et refresh tokens
- **Gestion de Mindmap** : Création, modification et visualisation de nœuds dans un mindmap interactif
- **Agents IA Configurables** : Création et exécution d'agents IA spécialisés via fichiers Markdown
- **Système de Triggers** : 
  - Triggers cron pour planification récurrente
  - Triggers date_reached pour tâches ponctuelles
  - Triggers email_received pour traitement automatique
  - Triggers manuels pour exécution à la demande
- **Actions Automatisées** : Système d'actions déclenchées par les triggers
- **Intégration Email** :
  - Réception automatique via IMAP (polling toutes les 2 minutes)
  - Envoi de résultats par SMTP
  - Formatage Markdown → HTML pour les emails
- **Structuration Automatique par IA** : Proposition automatique de type, tags et relations pour les nœuds
- **Recherche Web Intégrée** : Outils de recherche web pour les agents IA (DuckDuckGo)
- **Interface Web Moderne** : 
  - React + TypeScript + Material-UI
  - Canvas interactif pour le mindmap
  - Formulaires de configuration de triggers
  - Affichage formaté des résultats Markdown
- **Documentation Complète** :
  - Documentation d'architecture technique
  - Documentation fonctionnelle
  - Documentation API REST
  - Guide de contribution
  - EPICS et User Stories

### Modifié
- Amélioration de la gestion des sessions DB (sync/async)
- Optimisation du parsing de sortie Markdown/JSON
- Amélioration de la gestion des erreurs et logging

### Sécurité
- Hashage des mots de passe avec bcrypt
- Tokens JWT avec expiration
- Configuration CORS sécurisée
- Variables d'environnement pour les secrets

---

## [0.1.0] - 2025-XX-XX

### Ajouté
- Version initiale du projet
- Structure de base backend (FastAPI) et frontend (React)
- Configuration de base de données PostgreSQL
- Système de migrations Alembic

---

## Types de changements

- **Ajouté** : Nouvelles fonctionnalités
- **Modifié** : Changements dans les fonctionnalités existantes
- **Déprécié** : Fonctionnalités qui seront supprimées
- **Supprimé** : Fonctionnalités supprimées
- **Corrigé** : Corrections de bugs
- **Sécurité** : Corrections de vulnérabilités

---

## Format des versions

- **MAJOR** : Changements incompatibles avec les versions précédentes
- **MINOR** : Ajout de fonctionnalités rétrocompatibles
- **PATCH** : Corrections de bugs rétrocompatibles

---

**Note** : Ce changelog est maintenu manuellement. Pour les détails complets, consultez les [commits Git](../../commits/main).
