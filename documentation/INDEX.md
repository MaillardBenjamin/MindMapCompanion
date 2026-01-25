# Index de la Documentation

Bienvenue dans la documentation complète de **Personal Assistant**. Cette page vous guide vers la documentation appropriée selon vos besoins.

## 📖 Documentation par type

### Pour les développeurs

- **[Documentation d'Architecture Technique (DAT)](ARCHITECTURE.md)**
  - Vue d'ensemble technique
  - Structure du code
  - Patterns architecturaux
  - Base de données
  - Services backend
  - Communication API
  - Déploiement et sécurité

### Pour les utilisateurs et experts fonctionnels

- **[Documentation Fonctionnelle](FUNCTIONAL.md)**
  - Vue d'ensemble métier
  - Personas et cas d'usage
  - Fonctionnalités détaillées
  - Workflows métier
  - Règles métier
  - Contraintes et limites

### Pour démarrer rapidement

- **[Guide de démarrage rapide](README.md)**
  - Configuration
  - Installation
  - Lancement

### Pour documenter le code

- **[Guide de Documentation du Code](CODE_DOCUMENTATION.md)**
  - Standards de documentation (Python, TypeScript)
  - Exemples de docstrings
  - Checklist de documentation

### Pour la gestion produit

- **[EPICS et User Stories](EPICS_USER_STORIES.md)**
  - EPICS (grandes fonctionnalités)
  - User Stories détaillées
  - Backlog priorisé
  - Critères d'acceptation

### Pour les développeurs

- **[Guide de Contribution](../CONTRIBUTING.md)** - Comment contribuer au projet
- **[Guide de Développement Local](DEVELOPMENT.md)** - Setup environnement de développement
- **[Guide de Déploiement](DEPLOYMENT.md)** - Déploiement en production
- **[Guide de Dépannage](TROUBLESHOOTING.md)** - Résolution de problèmes courants
- **[Politique de Sécurité](../SECURITY.md)** - Sécurité et signalement de vulnérabilités
- **[Changelog](../CHANGELOG.md)** - Historique des versions
- **[Matrice des Flux](FLUX_MATRICE.md)** - Flux de données et interactions entre composants
- **[Diagrammes Mermaid](DIAGRAMMES.md)** - Diagrammes de classe et de séquence
- **[Configuration Markdown dans Cursor](MARKDOWN_SETUP.md)** - Guide pour visualiser les diagrammes Mermaid

## 🎯 Parcours de lecture recommandés

### Je suis nouveau sur le projet

1. Commencez par le [README principal](../../README.md)
2. Lisez le [Guide de démarrage rapide](README.md)
3. Explorez la [Documentation Fonctionnelle](FUNCTIONAL.md) pour comprendre ce que fait l'application
4. Consultez la [Documentation d'Architecture](ARCHITECTURE.md) pour comprendre comment c'est construit

### Je veux comprendre l'architecture

1. [Documentation d'Architecture Technique](ARCHITECTURE.md)
   - Section "Architecture générale"
   - Section "Structure du backend"
   - Section "Base de données"
   - Section "Services backend"

### Je veux comprendre les fonctionnalités métier

1. [Documentation Fonctionnelle](FUNCTIONAL.md)
   - Section "Fonctionnalités principales"
   - Section "Workflows métier"
   - Section "Règles métier"

### Je veux développer une nouvelle fonctionnalité

1. [Documentation d'Architecture Technique](ARCHITECTURE.md)
   - Section "Extensibilité"
   - Section "Structure du backend"
2. [Documentation Fonctionnelle](FUNCTIONAL.md)
   - Section "Évolutions fonctionnelles prévues"

### Je veux déployer l'application

1. [Documentation d'Architecture Technique](ARCHITECTURE.md)
   - Section "Déploiement"
   - Section "Variables d'environnement"

## 📚 Structure de la documentation

```
documentation/
├── INDEX.md              # Ce fichier - Index de navigation
├── ARCHITECTURE.md       # Documentation technique complète
├── FUNCTIONAL.md         # Documentation fonctionnelle complète
└── README.md             # Guide de démarrage rapide
```

## 🔍 Recherche rapide

### Concepts techniques

- **Architecture** → [ARCHITECTURE.md](ARCHITECTURE.md#architecture-générale)
- **Base de données** → [ARCHITECTURE.md](ARCHITECTURE.md#base-de-données)
- **Authentification** → [ARCHITECTURE.md](ARCHITECTURE.md#authentification-et-sécurité)
- **Agents IA** → [ARCHITECTURE.md](ARCHITECTURE.md#agents-ia-configurables)
- **Scheduler** → [ARCHITECTURE.md](ARCHITECTURE.md#planification-et-automatisation)

### Concepts fonctionnels

- **Mindmap** → [FUNCTIONAL.md](FUNCTIONAL.md#1-gestion-de-mindmap)
- **Agents IA** → [FUNCTIONAL.md](FUNCTIONAL.md#2-agents-ia-configurables)
- **Triggers** → [FUNCTIONAL.md](FUNCTIONAL.md#3-système-de-triggers-et-actions)
- **Emails** → [FUNCTIONAL.md](FUNCTIONAL.md#5-gestion-des-emails)
- **Workflows** → [FUNCTIONAL.md](FUNCTIONAL.md#workflows-métier)

## 📝 Glossaire

Un glossaire complet est disponible dans :
- [Documentation Fonctionnelle - Glossaire](FUNCTIONAL.md#glossaire)

## 🆘 Besoin d'aide ?

- **Problème technique** → Consultez [ARCHITECTURE.md](ARCHITECTURE.md#points-dattention)
- **Question fonctionnelle** → Consultez [FUNCTIONAL.md](FUNCTIONAL.md#contraintes-et-limites)
- **Configuration** → Consultez [README.md](README.md#configuration-backend)

## 🔄 Mise à jour

Cette documentation est maintenue à jour avec le code. Dernière mise à jour : voir les commits Git.

---

**Note** : Cette documentation couvre l'ensemble du code et des fonctionnalités de l'application Personal Assistant. Pour toute question ou suggestion d'amélioration, n'hésitez pas à ouvrir une issue ou une pull request.
