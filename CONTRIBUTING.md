# Guide de Contribution

Merci de votre intérêt pour contribuer à Personal Assistant ! Ce document décrit les standards et processus pour contribuer au projet.

## 📋 Table des matières

- [Code de conduite](#code-de-conduite)
- [Comment contribuer](#comment-contribuer)
- [Standards de code](#standards-de-code)
- [Processus de développement](#processus-de-développement)
- [Tests](#tests)
- [Documentation](#documentation)
- [Pull Requests](#pull-requests)

---

## 🤝 Code de conduite

- Soyez respectueux et inclusif
- Acceptez les critiques constructives
- Focalisez-vous sur ce qui est meilleur pour la communauté
- Montrez de l'empathie envers les autres membres

---

## 🚀 Comment contribuer

### Signaler un bug

1. Vérifiez que le bug n'a pas déjà été signalé dans les [Issues](../../issues)
2. Si non, créez une nouvelle issue avec :
   - Un titre clair et descriptif
   - Une description détaillée du problème
   - Les étapes pour reproduire
   - Le comportement attendu vs. observé
   - L'environnement (OS, versions, etc.)

### Proposer une fonctionnalité

1. Vérifiez que la fonctionnalité n'existe pas déjà
2. Créez une issue avec le label `enhancement`
3. Décrivez :
   - Le cas d'usage
   - La valeur ajoutée
   - Les alternatives considérées

### Contribuer du code

1. Fork le projet
2. Créez une branche depuis `main` : `git checkout -b feature/ma-fonctionnalite`
3. Commitez vos changements : `git commit -m 'feat: ajout de ma fonctionnalité'`
4. Push vers votre fork : `git push origin feature/ma-fonctionnalite`
5. Ouvrez une Pull Request

---

## 📝 Standards de code

### Conventions de nommage

**Python (Backend)** :
- Classes : `PascalCase` (ex: `ConfigurableAgentService`)
- Fonctions/variables : `snake_case` (ex: `execute_agent`)
- Constantes : `UPPER_SNAKE_CASE` (ex: `MAX_RETRIES`)
- Privé : préfixe `_` (ex: `_parse_output`)

**TypeScript (Frontend)** :
- Composants : `PascalCase` (ex: `NodeDetails`)
- Fonctions/variables : `camelCase` (ex: `handleSubmit`)
- Constantes : `UPPER_SNAKE_CASE` (ex: `API_BASE_URL`)
- Types/Interfaces : `PascalCase` (ex: `TriggerFormProps`)

### Formatage

**Python** :
- Utilisez `black` pour le formatage automatique
- Ligne max : 100 caractères
- Imports triés avec `isort`

```bash
black backend/app/
isort backend/app/
```

**TypeScript** :
- Utilisez `prettier` pour le formatage
- Ligne max : 100 caractères
- Utilisez ESLint pour le linting

```bash
npm run lint
npm run format
```

### Documentation du code

- Toutes les fonctions publiques doivent avoir des docstrings
- Suivez le [Guide de Documentation du Code](documentation/CODE_DOCUMENTATION.md)
- Commentez le "pourquoi", pas le "quoi"

---

## 🔄 Processus de développement

### Workflow Git

1. **Branches** :
   - `main` : Production (protégée)
   - `develop` : Développement (optionnel)
   - `feature/*` : Nouvelles fonctionnalités
   - `fix/*` : Corrections de bugs
   - `docs/*` : Documentation
   - `refactor/*` : Refactoring

2. **Commits** :
   - Format : `type(scope): description`
   - Types : `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
   - Exemples :
     ```
     feat(triggers): ajout du support cron
     fix(auth): correction de l'expiration du token
     docs(api): mise à jour de la documentation
     ```

3. **Messages de commit** :
   - Première ligne : < 50 caractères
   - Corps : expliquer le "pourquoi" si nécessaire
   - Référencer les issues : `Closes #123`

### Développement local

1. **Setup** :
   ```bash
   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Si disponible
   
   # Frontend
   cd frontend
   npm install
   ```

2. **Tests** :
   ```bash
   # Backend
   pytest backend/tests/
   
   # Frontend
   npm test
   ```

3. **Linting** :
   ```bash
   # Backend
   black --check backend/app/
   flake8 backend/app/
   
   # Frontend
   npm run lint
   ```

---

## 🧪 Tests

### Backend

- Utilisez `pytest` pour les tests
- Structure : `tests/test_*.py`
- Couverture minimale : 80%
- Tests unitaires pour la logique métier
- Tests d'intégration pour les API

**Exemple** :
```python
def test_create_node():
    """Test de création d'un nœud."""
    node = create_node(db, NodeCreate(raw_text="Test"))
    assert node.raw_text == "Test"
    assert node.status == NodeStatus.inbox
```

### Frontend

- Utilisez `Vitest` ou `Jest` pour les tests
- Tests unitaires pour les composants
- Tests d'intégration pour les workflows

**Exemple** :
```typescript
describe('NodeDetails', () => {
  it('should create a trigger', async () => {
    // Test implementation
  });
});
```

### Exécuter les tests

```bash
# Backend
pytest backend/tests/ -v --cov=app

# Frontend
npm test
```

---

## 📚 Documentation

### Mise à jour de la documentation

- Mettez à jour la documentation avec chaque changement
- Suivez la structure existante dans `documentation/`
- Ajoutez des exemples d'utilisation
- Documentez les breaking changes

### Types de documentation

- **Architecture** : `documentation/ARCHITECTURE.md`
- **Fonctionnelle** : `documentation/FUNCTIONAL.md`
- **API** : `documentation/API.md`
- **Code** : Docstrings dans le code

---

## 🔀 Pull Requests

### Avant de soumettre

- [ ] Les tests passent localement
- [ ] Le code respecte les standards (linting)
- [ ] La documentation est à jour
- [ ] Les commits suivent les conventions
- [ ] La PR est liée à une issue (si applicable)

### Template de PR

```markdown
## Description
Brève description des changements

## Type de changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Breaking change
- [ ] Documentation

## Checklist
- [ ] Tests ajoutés/mis à jour
- [ ] Documentation mise à jour
- [ ] Code revu par un pair

## Screenshots (si applicable)
...

## Références
Closes #123
```

### Review Process

1. Au moins 1 approbation requise
2. Tous les tests doivent passer
3. Pas de conflits avec `main`
4. Review automatique (CI/CD) doit passer

---

## 🐛 Debugging

### Backend

```bash
# Mode debug
uvicorn app.main:app --reload --log-level debug

# Logs détaillés
export LOG_LEVEL=DEBUG
```

### Frontend

```bash
# Mode développement avec source maps
npm run dev

# Console du navigateur
# DevTools > Console
```

---

## 📦 Dépendances

### Ajouter une dépendance

**Backend** :
1. Ajouter dans `requirements.txt`
2. Documenter dans `ARCHITECTURE.md` si importante
3. Vérifier les licences compatibles

**Frontend** :
1. `npm install <package>`
2. Documenter si nécessaire
3. Vérifier la compatibilité

### Mettre à jour les dépendances

- Testez après chaque mise à jour
- Vérifiez les breaking changes
- Mettez à jour la documentation si nécessaire

---

## 🔒 Sécurité

- Ne commitez **jamais** de secrets (API keys, passwords)
- Utilisez les variables d'environnement
- Signalez les vulnérabilités en privé
- Suivez le [Guide de Sécurité](SECURITY.md)

---

## ❓ Questions ?

- Ouvrez une issue avec le label `question`
- Consultez la [documentation](documentation/INDEX.md)
- Contactez les mainteneurs

---

**Merci de contribuer à Personal Assistant ! 🎉**
