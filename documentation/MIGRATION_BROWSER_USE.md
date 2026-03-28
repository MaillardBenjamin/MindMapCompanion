# Migration de Playwright vers Browser-Use avec Ollama

Ce guide explique comment migrer vos scrapers de **Playwright** vers **Browser-Use avec Ollama** pour bénéficier de l'automatisation intelligente par IA.

## Table des matières

1. [Pourquoi Browser-Use ?](#pourquoi-browser-use)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Migration d'un scraper](#migration-dun-scraper)
5. [Différences principales](#différences-principales)
6. [Exemples](#exemples)
7. [Dépannage](#dépannage)

## Pourquoi Browser-Use ?

### Avantages de Browser-Use avec Ollama

✅ **Automatisation intelligente** : L'IA comprend les intentions et s'adapte aux changements de structure des sites  
✅ **Instructions en langage naturel** : Plus besoin de sélecteurs CSS/XPath complexes  
✅ **Gratuit** : Utilise Ollama en local, pas de coûts d'API  
✅ **Robustesse** : L'IA peut gérer les variations et erreurs  
✅ **Maintenance simplifiée** : Moins de code à maintenir  

### Inconvénients

⚠️ **Performance** : Peut être plus lent que Playwright (utilisation du LLM)  
⚠️ **Prévisibilité** : Le comportement peut varier légèrement entre les exécutions  
⚠️ **Ressources** : Nécessite Ollama en local (RAM, CPU)  

### Quand utiliser Browser-Use ?

- Sites avec une structure complexe ou changeante
- Tâches nécessitant de la compréhension contextuelle
- Prototypage rapide de scrapers
- Sites avec des anti-bots sophistiqués (l'IA peut mieux s'adapter)

### Quand rester sur Playwright ?

- Scraping de haute performance (volume important)
- Sites avec une structure très stable
- Besoin de comportement 100% déterministe
- Environnement sans GPU ou avec ressources limitées

## Installation

### 1. Installer les dépendances Python

```bash
cd backend
pip install -r requirements.txt
```

Les nouvelles dépendances ajoutées :
- `browser-use>=0.1.0` : Bibliothèque d'automatisation avec IA
- `langchain-ollama>=0.1.0` : Intégration Ollama avec LangChain
- `langchain>=0.3.0` : Framework pour applications LLM

### 2. Installer Ollama (si pas déjà fait)

**macOS :**
```bash
brew install ollama
```

**Linux :**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows :**
Téléchargez depuis [ollama.com](https://ollama.com)

### 3. Télécharger un modèle

Le modèle recommandé pour le scraping est `qwen3:14b` (bon équilibre performance/qualité) :

```bash
ollama pull qwen3:14b
```

Autres modèles possibles :
- `llama3.1:8b` : Plus rapide, moins précis
- `qwen2.5:32b` : Plus précis, plus lent
- `mistral:7b` : Alternative légère

### 4. Démarrer Ollama

```bash
ollama serve
```

Vérifiez que le service est actif :
```bash
curl http://localhost:11434/v1/models
```

### 5. Configuration dans .env

Vérifiez que votre fichier `.env` contient :

```bash
OLLAMA_BASE_URL=http://localhost:11434/v1
AGNO_MODEL=qwen3:14b
```

## Configuration

### Structure d'un scraper Browser-Use

Un scraper Browser-Use utilise le même format de fichier markdown que Playwright, mais avec des différences clés :

```markdown
---
name: Mon Scraper (Browser-Use)
site_url: https://example.com
executor_type: browser-use  # ← Important ! Définit le type d'executor
storage:
  base_dir: data/job_offers/example
  subdir_pattern: ""
  file_pattern: "{id}.md"
browser:
  headless: false
  viewport:
    width: 1920
    height: 1080
  timeout: 60000  # Plus long pour laisser le temps à l'IA
---

# Instructions pour Browser-Use

## Objectif
Extraire les offres d'emploi depuis le site Example.com

## Instructions détaillées
1. Va sur le site {{site_url}}
2. Accepte les cookies si une bannière apparaît
3. Remplis le formulaire de recherche avec :
   - Mots-clés : {{search.keywords}}
   - Localisation : {{search.location}}
4. Clique sur "Rechercher"
5. Pour chaque offre sur la page :
   - Extrais le titre, l'entreprise, la localisation
   - Récupère le lien vers l'offre complète
6. Retourne les données au format JSON

## Format de sortie
\```json
{
  "offers": [
    {
      "id": "123",
      "title": "...",
      "company": "...",
      "location": "...",
      "url": "https://...",
      ...
    }
  ]
}
\```
```

## Migration d'un scraper

### Étape 1 : Copier le fichier de configuration

```bash
cd backend/app/agent_configs/scrapers
cp mon-scraper.md mon-scraper-browseruse.md
```

### Étape 2 : Modifier le frontmatter

Dans le nouveau fichier, ajoutez :

```yaml
executor_type: browser-use
```

Ajustez les timeouts (l'IA prend plus de temps) :

```yaml
browser:
  timeout: 60000
  navigation_timeout: 60000
```

### Étape 3 : Convertir les étapes en instructions naturelles

*Exemple simplifié ci-dessous. La conversion complète du scraper Cadre Emploi (toutes les étapes Playwright) est dans `scrapers/cadre-emploi-scraper-browseruse.md`.*

**Avant (Playwright) :**

```yaml
action: goto
url: "{{site_url}}"
---
action: click
selector: "#accept-cookies"
---
action: fill
selector: "input[name='keywords']"
value: "{{search.keywords}}"
---
action: click
selector: "button[type='submit']"
```

**Après (Browser-Use) :**

```markdown
1. Va sur le site {{site_url}}
2. Si une bannière de cookies apparaît, clique sur le bouton pour accepter
3. Remplis le champ de recherche avec les mots-clés : {{search.keywords}}
4. Clique sur le bouton de recherche
```

### Étape 4 : Définir le format de sortie

Browser-Use a besoin d'instructions claires sur le format de sortie :

```markdown
## Format de sortie

Retourne un JSON avec cette structure :

\```json
{
  "offers": [
    {
      "id": "identifiant unique",
      "title": "titre du poste",
      "company": "nom de l'entreprise",
      "location": "ville, région",
      "url": "lien complet vers l'offre",
      "description": "description courte",
      "salary": "fourchette de salaire",
      "contract_type": "CDI/CDD/etc",
      "publish_date": "date au format YYYY-MM-DD"
    }
  ]
}
\```
```

### Étape 5 : Tester

```bash
# Depuis la racine du projet
python -m app.tools.job_scraping_tools scrape mon-scraper-browseruse.md
```

## Différences principales

| Aspect           | Playwright             | Browser-Use               |
| ---------------- | ---------------------- | ------------------------- |
| **Instructions** | Étapes YAML détaillées | Langage naturel           |
| **Sélecteurs**   | CSS/XPath précis       | Description textuelle     |
| **Logique**      | Explicite (if/for/etc) | Implicite (l'IA comprend) |
| **Adaptabilité** | Rigide                 | Flexible                  |
| **Performance**  | Rapide (~2-5s)         | Plus lent (~10-30s)       |
| **Déterminisme** | 100%                   | ~95%                      |
| **Maintenance**  | Moyenne-élevée         | Faible                    |

## Exemples

### Exemple 1 : Scraper simple

**Playwright :**
```yaml
action: goto
url: "https://example.com/jobs"
---
action: extract_list
container_selector: ".job-list"
item_selector: ".job-card"
fields:
  - name: title
    selector: ".job-title"
    type: text
  - name: company
    selector: ".company-name"
    type: text
```

**Browser-Use :**
```markdown
1. Va sur https://example.com/jobs
2. Pour chaque carte d'offre d'emploi :
   - Extrais le titre du poste
   - Extrais le nom de l'entreprise
3. Retourne la liste des offres au format JSON
```

### Exemple 2 : Avec authentification

**Browser-Use :**
```markdown
1. Va sur https://example.com/login
2. Remplis le formulaire de connexion :
   - Email : {{credentials.email}}
   - Mot de passe : {{credentials.password}}
3. Clique sur "Se connecter"
4. Attends que la page d'accueil se charge
5. Va sur la section "Mes offres"
6. Extrais toutes les offres...
```

### Exemple 3 : Gestion de pagination

**Browser-Use :**
```markdown
1. Va sur la page de recherche
2. Extrais les offres de la page actuelle
3. S'il y a un bouton "Page suivante" :
   - Clique dessus
   - Attends le chargement
   - Répète l'extraction
4. Continue jusqu'à la page 5 ou jusqu'à ce qu'il n'y ait plus de bouton "Suivant"
```

## Dépannage

### Problème : Ollama n'est pas accessible

**Erreur :**
```
[BrowserUseExecutor] Erreur lors du scraping: Could not connect to Ollama at http://localhost:11434
```

**Solution :**
1. Vérifiez qu'Ollama est démarré : `ps aux | grep ollama`
2. Démarrez-le : `ollama serve`
3. Vérifiez l'URL dans `.env` : `OLLAMA_BASE_URL=http://localhost:11434/v1`

### Problème : Le modèle n'est pas trouvé

**Erreur :**
```
model 'qwen3:14b' not found
```

**Solution :**
```bash
ollama pull qwen3:14b
```

### Problème : Le scraping est très lent

**Causes possibles :**
1. Modèle trop gros pour votre machine → Utilisez un modèle plus petit (`llama3.1:8b`)
2. Mode headless désactivé → Activez-le : `headless: true`
3. Vision activée → Elle est désactivée par défaut, vérifiez le code

**Optimisations :**
```yaml
browser:
  headless: true  # Plus rapide sans interface graphique
  timeout: 45000  # Timeout plus court
```

Dans le code, vous pouvez aussi ajuster la température du modèle :
```python
llm = ChatOllama(
    model=self.settings.agno_model,
    temperature=0.0,  # Plus déterministe = plus rapide
)
```

### Problème : Les résultats ne sont pas au bon format

**Cause :** L'IA n'a pas compris le format attendu

**Solution :** Soyez plus explicite dans les instructions :

```markdown
## Format de sortie STRICT

Tu DOIS retourner UNIQUEMENT un objet JSON valide avec cette structure exacte :

\```json
{
  "offers": [
    {"id": "...", "title": "...", "company": "...", "location": "...", "url": "..."}
  ]
}
\```

NE RETOURNE PAS de texte avant ou après le JSON.
NE RETOURNE PAS d'explications.
RETOURNE UNIQUEMENT le JSON.
```

### Problème : Le scraper extrait des données incomplètes

**Solution :** Soyez plus précis dans les instructions :

```markdown
Pour chaque offre, tu DOIS extraire TOUS les champs suivants :
- id : OBLIGATOIRE, cherche dans l'URL ou les attributs data-*
- title : OBLIGATOIRE, le titre du poste
- company : OBLIGATOIRE, nom de l'entreprise
- location : OBLIGATOIRE, ville ou "Non spécifié" si introuvable
- url : OBLIGATOIRE, lien absolu (commence par https://)
- description : optionnel
- salary : optionnel
- contract_type : optionnel
- publish_date : optionnel

Si un champ obligatoire est introuvable, mets une valeur par défaut plutôt que de sauter l'offre.
```

### Problème : Erreur JSON parsing

**Erreur :**
```
[BrowserUseExecutor] Le résultat n'est pas un JSON valide
```

**Solution :** Le parsing essaie déjà d'extraire le JSON du texte, mais vous pouvez améliorer en :

1. Rendant les instructions plus strictes (voir ci-dessus)
2. Vérifiant les logs pour voir ce que l'IA retourne réellement
3. Ajustant le modèle (certains modèles sont meilleurs pour le JSON)

### Problème : L'IA ne trouve pas les éléments sur la page

**Solutions :**

1. **Soyez plus descriptif :**
   ```markdown
   Cherche le bouton de recherche. Il peut avoir le texte "Rechercher", "Search", 
   ou être représenté par une icône de loupe. Il se trouve généralement en haut 
   à droite de la barre de recherche.
   ```

2. **Donnez des alternatives :**
   ```markdown
   Pour accepter les cookies, cherche :
   - Un bouton "Accepter" ou "J'accepte"
   - Un bouton "Accept" ou "I agree"
   - Un bouton avec l'icône ✓
   - Si introuvable, cherche un bouton de fermeture (X) sur la bannière
   ```

3. **Utilisez des repères visuels :**
   ```markdown
   Le titre de l'offre est le texte en gros et en gras dans chaque carte d'offre.
   Le nom de l'entreprise est généralement en dessous du titre, en plus petit.
   ```

## Passage en production

### Recommandations

1. **Testez d'abord** : Validez le scraper sur plusieurs exécutions
2. **Logs** : Activez les logs détaillés pour surveiller le comportement
3. **Fallback** : Gardez la version Playwright en cas de problème
4. **Monitoring** : Suivez les temps d'exécution et le taux de succès
5. **Modèle** : Choisissez le bon modèle selon vos besoins (vitesse vs précision)

### Configuration recommandée pour la production

```yaml
browser:
  headless: true
  timeout: 60000
  navigation_timeout: 60000
```

```python
# Dans BrowserUseExecutor, ajuster :
llm = ChatOllama(
    model="qwen3:14b",  # Bon équilibre
    temperature=0.1,      # Déterministe mais pas rigide
)
```

### Scaling

Pour scraper plusieurs sites en parallèle :

1. **Plusieurs instances Ollama** : Démarrez Ollama sur différents ports
2. **Queue système** : Utilisez Celery ou RQ pour distribuer les tâches
3. **GPU** : Si disponible, Ollama utilisera le GPU pour accélérer l'inférence

## Support

Pour plus d'informations :

- **Browser-Use** : [github.com/browser-use/browser-use](https://github.com/browser-use/browser-use)
- **Ollama** : [ollama.com](https://ollama.com)
- **Documentation Ollama** : [github.com/ollama/ollama/blob/main/docs/api.md](https://github.com/ollama/ollama/blob/main/docs/api.md)

## Conclusion

Browser-Use avec Ollama offre une approche plus intuitive et maintenable pour le scraping web, au prix d'une légère perte de performance. C'est un excellent choix pour :

- Les sites complexes ou changeants
- Le prototypage rapide
- Les scrapers nécessitant de la compréhension contextuelle

Pour les scrapers critiques nécessitant des performances maximales, Playwright reste le meilleur choix. Les deux systèmes peuvent coexister dans votre application !
