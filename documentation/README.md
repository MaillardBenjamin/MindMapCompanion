# Documentation PersonalAssistant

Bienvenue dans la documentation du projet PersonalAssistant.

## 🆕 Nouveau : Scraping intelligent avec Browser-Use + Ollama

Le projet supporte maintenant **l'automatisation intelligente de scraping web** via Browser-Use avec Ollama :

✅ **Gratuit** : Utilise Ollama en local (pas de coûts d'API)  
✅ **Simple** : Instructions en langage naturel au lieu de sélecteurs CSS  
✅ **Intelligent** : L'IA s'adapte aux changements de structure des sites  
✅ **Coexistant** : Fonctionne en parallèle avec Playwright  

**Pour démarrer rapidement :**
1. Lisez le [Guide de démarrage rapide](./BROWSER_USE_QUICKSTART.md) (5 minutes)
2. Installez Ollama : `brew install ollama` (macOS)
3. Téléchargez un modèle : `ollama pull qwen3:14b`
4. Testez : `python tests/test_browser_use_integration.py`

**Documentation complète :** [MIGRATION_BROWSER_USE.md](./MIGRATION_BROWSER_USE.md)

## 📚 Documentation disponible

### Scraping avec IA (Browser-Use)
- **[BROWSER_USE_QUICKSTART.md](./BROWSER_USE_QUICKSTART.md)** : 🚀 Guide de démarrage rapide (5 min)
- **[MIGRATION_BROWSER_USE.md](./MIGRATION_BROWSER_USE.md)** : 📖 Documentation complète de migration

### Architecture et Développement
- **ARCHITECTURE.md** : Architecture complète du système (si disponible)
- **PREPROMPT_ET_PERSONNALISATION.md** : Configuration des agents

## Configuration backend

### Variables d'environnement (.env)

Créez un fichier `backend/.env` avec :

```bash
# Base de données
DATABASE_URL=postgresql://postgres:password@localhost:5432/personal_assistant_db

# JWT
SECRET_KEY=votre-clé-secrète
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Auth
AUTH_USERNAME=admin
AUTH_PASSWORD=admin

# IMAP (pour les agents email)
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USER=user@example.com
IMAP_PASSWORD=app-password
IMAP_FOLDER=INBOX
IMAP_SSL=true
IMAP_POLL_MINUTES=2

# IA / LLM
# Option 1 : OpenAI (payant)
AGNO_MODEL=gpt-4o-mini
AGNO_API_KEY=your-openai-key

# Option 2 : Ollama local (gratuit, recommandé)
OLLAMA_BASE_URL=http://localhost:11434/v1
AGNO_MODEL=qwen3:14b

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Agent configuration
AGENT_LANGUE=fr
AGENT_ADRESSE=tu
AGENT_PRENOM=Benjamin
AGENT_TON=professionnel
```

### Installation et lancement

#### Backend

```bash
# Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate  # Windows

# Installer les dépendances
cd backend
pip install -r requirements.txt

# Migrations de base de données
alembic upgrade head

# Lancer le serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Le frontend sera accessible sur http://localhost:5173 (ou 3000)

## Organisation du projet

```
PersonalAssistant/
├── backend/
│   ├── app/
│   │   ├── api/                    # Routes API
│   │   ├── core/                   # Configuration, modèles
│   │   ├── services/
│   │   │   ├── job_scraping/       # Système de scraping
│   │   │   │   ├── playwright_executor.py      # Executor Playwright
│   │   │   │   └── browser_use_executor.py     # Executor Browser-Use (IA)
│   │   │   └── configurable_agent_service.py
│   │   ├── agent_configs/          # Configurations des agents
│   │   │   ├── agents/             # Agents standards
│   │   │   └── scrapers/           # Scrapers web
│   │   │       ├── *.md                    # Format Playwright
│   │   │       └── *-browseruse.md         # Format Browser-Use
│   │   └── tools/                  # Outils pour les agents
│   ├── alembic/                    # Migrations DB
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   └── package.json
├── documentation/                  # Documentation (ce dossier)
│   ├── README.md                   # Ce fichier
│   ├── BROWSER_USE_QUICKSTART.md   # Guide rapide Browser-Use
│   └── MIGRATION_BROWSER_USE.md    # Documentation Browser-Use complète
└── tests/
    ├── test_browser_use_integration.py  # Tests Browser-Use
    └── ...
```

## Comparaison Playwright vs Browser-Use

| Aspect           | Playwright               | Browser-Use + Ollama          |
| ---------------- | ------------------------ | ----------------------------- |
| **Syntaxe**      | YAML avec sélecteurs CSS | Langage naturel               |
| **Performance**  | Rapide (2-5s)            | Moyen (10-30s)                |
| **Maintenance**  | Moyenne                  | Faible                        |
| **Adaptabilité** | Rigide                   | Flexible                      |
| **Coût**         | Gratuit                  | Gratuit (local)               |
| **Cas d'usage**  | Sites stables, volume    | Sites changeants, prototypage |

**Recommandation :** Utilisez Browser-Use pour le prototypage et les sites complexes, Playwright pour la production et le volume.

## Exemple de scraper Browser-Use

**Fichier : `backend/app/agent_configs/scrapers/exemple-browseruse.md`**

```markdown
---
name: Exemple Scraper (Browser-Use)
site_url: https://example.com/jobs
executor_type: browser-use
storage:
  base_dir: data/job_offers/example
browser:
  headless: false
  timeout: 60000
---

# Instructions pour Browser-Use

## Objectif
Extraire les offres d'emploi depuis Example.com

## Instructions
1. Va sur {{site_url}}
2. Si une bannière de cookies apparaît, accepte-la
3. Pour chaque offre d'emploi visible sur la page :
   - Extrais le titre du poste
   - Extrais le nom de l'entreprise
   - Extrais la localisation
   - Récupère le lien vers l'offre complète

## Format de sortie
\```json
{
  "offers": [
    {
      "id": "123",
      "title": "Développeur Python",
      "company": "Entreprise XYZ",
      "location": "Paris",
      "url": "https://example.com/jobs/123"
    }
  ]
}
\```
```

## Tests

### Tests rapides (sans Ollama)

```bash
pytest tests/test_browser_use_integration.py -v -m "not slow"
```

### Tests complets (avec Ollama)

```bash
# Assurez-vous qu'Ollama est démarré
ollama serve

# Exécuter les tests
pytest tests/test_browser_use_integration.py -v
```

### Test manuel rapide

```bash
python tests/test_browser_use_integration.py
```

## Liens utiles

- [README principal](../README.md)
- [Backend README](../backend/README.md)
- [Guide de démarrage Browser-Use](./BROWSER_USE_QUICKSTART.md) 🆕
- [Migration Playwright → Browser-Use](./MIGRATION_BROWSER_USE.md) 🆕
- [Browser-Use GitHub](https://github.com/browser-use/browser-use)
- [Ollama](https://ollama.com)

## Support

Pour toute question ou problème :

1. Consultez la [documentation complète](./MIGRATION_BROWSER_USE.md)
2. Vérifiez les [tests d'intégration](../tests/test_browser_use_integration.py)
3. Regardez les [exemples de scrapers](../backend/app/agent_configs/scrapers/)

## Prochaines étapes

1. ✅ Suivre le [guide de démarrage rapide](./BROWSER_USE_QUICKSTART.md)
2. ✅ Tester avec le scraper d'exemple Cadre Emploi
3. ✅ Créer votre premier scraper Browser-Use
4. ✅ Migrer vos scrapers Playwright existants (optionnel)
