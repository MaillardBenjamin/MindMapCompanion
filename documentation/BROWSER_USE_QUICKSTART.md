# Guide de démarrage rapide - Browser-Use avec Ollama

Ce guide vous permettra de démarrer rapidement avec Browser-Use et Ollama pour automatiser vos scrapers avec l'IA.

## ⚡ Installation rapide (5 minutes)

### 1. Installer les dépendances Python

```bash
cd backend
pip install -r requirements.txt
```

### 2. Installer et démarrer Ollama

**macOS :**
```bash
brew install ollama
ollama serve
```

**Linux :**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

### 3. Télécharger le modèle

```bash
ollama pull qwen3:14b
```

### 4. Vérifier la configuration

Assurez-vous que votre `.env` contient :

```bash
OLLAMA_BASE_URL=http://localhost:11434/v1
AGNO_MODEL=qwen3:14b
```

### 5. Tester l'installation

```bash
cd /Users/benjaminmaillard/Documents/PersonalAssistant
python tests/test_browser_use_integration.py
```

Vous devriez voir :
```
✅ Ollama URL : http://localhost:11434/v1
✅ Modèle : qwen3:14b
✅ browser-use et langchain-ollama sont installés
✅ Configuration parsée : Cadre Emploi Scraper (Browser-Use)
```

## 🚀 Premier scraper en 3 étapes

### Étape 1 : Créer un fichier de configuration

Créez `backend/app/agent_configs/scrapers/mon-scraper.md` :

```markdown
---
name: Mon Premier Scraper
site_url: https://example.com/jobs
executor_type: browser-use
storage:
  base_dir: data/job_offers/example
  subdir_pattern: ""
  file_pattern: "{id}.md"
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
3. Pour chaque offre d'emploi visible :
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
      "title": "Titre du poste",
      "company": "Nom entreprise",
      "location": "Ville",
      "url": "https://..."
    }
  ]
}
\```
```

### Étape 2 : Créer un script de test

Créez `test_scraper.py` :

```python
import asyncio
from app.services.job_scraping import get_job_scraping_service

async def main():
    service = get_job_scraping_service()
    
    result = await service.scrape_with_config(
        config_path="scrapers/mon-scraper.md",
        search_params={}
    )
    
    print(f"✅ Scraping terminé : {result.offers_count} offres extraites")
    for offer in result.offers:
        print(f"  - {offer.title} @ {offer.company}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Étape 3 : Exécuter

```bash
cd backend
python test_scraper.py
```

## 📋 Exemples d'instructions

### Navigation simple

```markdown
1. Va sur https://example.com
2. Clique sur "Se connecter"
3. Remplis le formulaire avec :
   - Email : {{credentials.email}}
   - Mot de passe : {{credentials.password}}
4. Clique sur "Connexion"
```

### Extraction de liste

```markdown
1. Va sur la page de résultats
2. Pour chaque carte d'offre d'emploi :
   - Extrais le titre (texte en gros et en gras)
   - Extrais l'entreprise (en dessous du titre)
   - Extrais la localisation (icône de lieu)
   - Récupère le lien (attribut href du titre)
```

### Gestion de pagination

```markdown
1. Extrais les offres de la page actuelle
2. Cherche un bouton "Page suivante" ou "Suivant"
3. Si tu le trouves :
   - Clique dessus
   - Attends que la page se charge
   - Répète l'extraction
4. Continue jusqu'à 5 pages maximum
```

### Gestion d'erreurs

```markdown
1. Va sur le site
2. Si une bannière de cookies apparaît :
   - Cherche "Accepter" ou "J'accepte"
   - Sinon cherche le bouton de fermeture (X)
   - Si rien ne fonctionne, continue quand même
3. Si un CAPTCHA apparaît, note-le dans les logs et arrête
```

## 🎯 Conseils pour de bonnes instructions

### ✅ Bonnes pratiques

1. **Soyez explicite sur ce que vous cherchez**
   ```markdown
   Cherche le bouton de connexion. Il a généralement le texte "Se connecter" 
   ou "Login" et se trouve en haut à droite de la page.
   ```

2. **Donnez des alternatives**
   ```markdown
   Pour accepter les cookies :
   - Cherche un bouton "Accepter"
   - Ou un bouton "J'accepte"
   - Ou un bouton "OK"
   ```

3. **Décrivez visuellement les éléments**
   ```markdown
   Le titre de l'offre est le texte le plus gros dans chaque carte, 
   généralement en bleu et cliquable.
   ```

4. **Spécifiez le format de sortie clairement**
   ```markdown
   RETOURNE UNIQUEMENT un objet JSON valide.
   NE RETOURNE PAS de texte explicatif.
   ```

### ❌ À éviter

1. **Instructions vagues**
   ```markdown
   ❌ Extrais les offres
   ✅ Pour chaque carte d'offre, extrais le titre, l'entreprise et la localisation
   ```

2. **Sélecteurs CSS/XPath**
   ```markdown
   ❌ Clique sur "button.submit-btn"
   ✅ Clique sur le bouton de soumission (généralement marqué "Soumettre" ou "Envoyer")
   ```

3. **Logique complexe**
   ```markdown
   ❌ Si X alors Y sinon si Z alors W...
   ✅ Cherche X. Si tu ne le trouves pas, cherche Z.
   ```

## 🔧 Paramètres utiles

### Dans le frontmatter

```yaml
browser:
  headless: false        # true = pas d'interface (plus rapide)
  timeout: 60000         # Timeout global (ms)
  navigation_timeout: 60000  # Timeout de navigation (ms)
  viewport:
    width: 1920
    height: 1080
```

### Paramètres de recherche

```python
result = await service.scrape_with_config(
    config_path="scrapers/mon-scraper.md",
    search_params={
        "keywords": "Python Developer",
        "location": "Paris",
        "contract_type": "CDI"
    }
)
```

Ces paramètres sont accessibles dans les instructions via `{{search.keywords}}`, etc.

## 🐛 Dépannage rapide

### Le scraping est lent

1. Activez le mode headless : `headless: true`
2. Utilisez un modèle plus petit : `ollama pull llama3.1:8b`
3. Réduisez la température dans le code : `temperature=0.0`

### Les résultats sont incomplets

Soyez plus précis dans les instructions :

```markdown
Pour chaque offre, tu DOIS extraire :
- id : OBLIGATOIRE (cherche dans l'URL)
- title : OBLIGATOIRE
- company : OBLIGATOIRE
- location : OBLIGATOIRE ou "Non spécifié"
- url : OBLIGATOIRE (URL complète commençant par https://)
```

### L'IA ne trouve pas les éléments

Décrivez visuellement les éléments :

```markdown
Le bouton de recherche est un bouton bleu en haut à droite avec le texte 
"Rechercher" ou une icône de loupe. Il est juste à côté de la barre de recherche.
```

### Erreur de connexion à Ollama

```bash
# Vérifier qu'Ollama est démarré
ps aux | grep ollama

# Le démarrer si nécessaire
ollama serve

# Tester la connexion
curl http://localhost:11434/v1/models
```

## 📚 Ressources

- **Documentation complète** : [MIGRATION_BROWSER_USE.md](./MIGRATION_BROWSER_USE.md)
- **Browser-Use GitHub** : [github.com/browser-use/browser-use](https://github.com/browser-use/browser-use)
- **Ollama** : [ollama.com](https://ollama.com)
- **Exemple de scraper** : `backend/app/agent_configs/scrapers/cadre-emploi-scraper-browseruse.md`

## 🎉 Prochaines étapes

1. Testez avec le scraper d'exemple : Cadre Emploi
2. Migrez un de vos scrapers Playwright existants
3. Créez un nouveau scraper pour un site de votre choix
4. Optimisez les performances selon vos besoins

**Besoin d'aide ?** Consultez la documentation complète dans `MIGRATION_BROWSER_USE.md` !
