---
name: Cadre Emploi Scraper
site_url: https://www.cadremploi.fr/emploi/liste_offres
storage:
  base_dir: data/job_offers/cadre-emploi
  subdir_pattern: "{date}"
  file_pattern: "{title_slug}-{id}.md"
  archive_dir: data/job_offers/archive/cadre-emploi
  retention_days: 30
  cleanup_enabled: true
  cleanup_schedule: "0 2 * * 0"
browser:
  headless: false
  viewport:
    width: 1920
    height: 1080
  user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  timeout: 30000
  navigation_timeout: 60000
  wait_until: networkidle
credentials:
  email_env: CADRE_EMPLOI_EMAIL
  password_env: CADRE_EMPLOI_PASSWORD
anti_bot:
  enabled: true
  random_delays:
    min: 2000
    max: 5000
    between_actions: true
  mouse_movements: false
  human_typing: true
rate_limiting:
  enabled: true
  requests_per_minute: 6
  delay_between_requests: 10000
error_handling:
  retry_on_failure: 3
  retry_delay: 5000
---

# Instructions Playwright pour Cadre Emploi

## Navigation

### Étape 1: Accès au site
```yaml
action: goto
url: "{{site_url}}"
options:
  wait_until: networkidle
  timeout: 30000
wait_for:
  selector: "body"
  state: visible
  timeout: 10000
```

### Étape 2: Gestion des cookies
```yaml
action: handle_popup
type: cookie_banner
selector: "#didomi-host, .didomi-popup, [id*='cookie'], [class*='cookie-banner']"
strategy: accept
fallback:
  - action: click
    selector: "#didomi-notice-agree-button, button[id*='accept'], button[class*='accept'], [aria-label*='accept']"
    timeout: 5000
  - action: wait
    timeout: 2000
```

## Authentification

### Étape 3: Accès à la page de connexion
```yaml
action: click
selector: "a[href*='connexion'], a[href*='login'], button:has-text('Connexion'), button:has-text('Se connecter')"
wait_for:
  selector: "form, input[type='email'], input[name='email']"
  state: visible
  timeout: 10000
on_error:
  - action: goto
    url: "{{site_url}}/connexion"
  - action: wait
    timeout: 3000
```

### Étape 4: Remplissage email
```yaml
action: fill
selector: "input[type='email'], input[name='email'], input[id*='email'], input[placeholder*='mail']"
value: "{{credentials.email}}"
options:
  clear: true
  timeout: 5000
```

### Étape 5: Remplissage mot de passe
```yaml
action: fill
selector: "input[type='password'], input[name='password'], input[id*='password']"
value: "{{credentials.password}}"
options:
  clear: true
  timeout: 5000
```

### Étape 6: Soumission du formulaire
```yaml
action: click
selector: "button[type='submit'], input[type='submit'], button:has-text('Connexion'), button:has-text('Se connecter')"
wait_for:
  selector: "[class*='dashboard'], [class*='profile'], [class*='account'], nav[class*='user']"
  state: visible
  timeout: 20000
on_error:
  - action: screenshot
    path: "errors/cadre-emploi-auth-failed-{{timestamp}}.png"
  - action: wait
    timeout: 5000
  - action: log
    level: error
    message: "Authentification échouée sur Cadre Emploi"
```

## Recherche

### Étape 7: Accès à la recherche
```yaml
action: goto
url: "{{site_url}}"
options:
  wait_until: networkidle
  timeout: 30000
wait_for:
  selector: "input[name*='keyword'], input[id*='search'], input[placeholder*='recherche'], form[class*='search']"
  state: visible
  timeout: 10000
```

### Étape 8: Remplissage des mots-clés
```yaml
action: fill
selector: "input[name*='keyword'], input[id*='keyword'], input[placeholder*='métier'], input[placeholder*='poste']"
value: "{{search.keywords}}"
options:
  clear: true
  timeout: 5000
```

### Étape 9: Remplissage de la localisation
```yaml
action: fill
selector: "input[name*='location'], input[id*='location'], input[placeholder*='lieu'], input[placeholder*='ville']"
value: "{{search.location}}"
options:
  clear: true
  timeout: 5000
```

### Étape 10: Lancement de la recherche
```yaml
action: click
selector: "button[type='submit'], button:has-text('Rechercher'), button[class*='search'], input[type='submit']"
wait_for:
  selector: "[class*='result'], [class*='job-list'], [class*='offer'], article"
  state: visible
  timeout: 20000
```

## Extraction

### Étape 11: Scroll pour charger le contenu
```yaml
action: scroll
direction: bottom
wait_for:
  selector: "[class*='result'], [class*='job-list'], article"
  state: visible
  timeout: 5000
```

### Étape 12: Extraction des offres
```yaml
action: extract_list
container_selector: "[class*='job-list'], [class*='results'], main"
item_selector: "[class*='job-item'], [class*='offer-item'], article[class*='job'], li[class*='result'], [data-job-id]"
fields:
  - name: title
    selector: "h2, h3, [class*='title'], a[class*='title']"
    type: text
    required: true
    transform: trim
  - name: company
    selector: "[class*='company'], [class*='employer'], [class*='enterprise'], span[class*='name']"
    type: text
    required: true
    transform: trim
  - name: location
    selector: "[class*='location'], [class*='place'], [class*='city'], [class*='lieu']"
    type: text
    fallback: "Non spécifié"
    transform: trim
  - name: salary
    selector: "[class*='salary'], [class*='salaire'], [class*='remuneration']"
    type: text
    optional: true
    transform: trim
  - name: contract_type
    selector: "[class*='contract'], [class*='contrat'], [class*='type']"
    type: text
    optional: true
    transform: trim
  - name: description
    selector: "[class*='description'], [class*='summary'], [class*='excerpt'], p"
    type: text
    optional: true
    transform: trim
  - name: url
    selector: "a[href*='offre'], a[href*='job'], h2 a, h3 a"
    type: attribute
    attribute: href
    transform: absolute_url
  - name: publish_date
    selector: "[class*='date'], time, [class*='published']"
    type: text
    optional: true
    transform: trim
  - name: source_id
    selector: "[data-job-id], [data-offer-id], [data-id]"
    type: attribute
    attribute: data-job-id
    optional: true
metadata:
  source: cadre-emploi
  scraped_at: "{{timestamp}}"
  search_keywords: "{{search.keywords}}"
  search_location: "{{search.location}}"
```

## Pagination

### Étape 13: Navigation vers les pages suivantes
```yaml
action: paginate
strategy: click_next
next_button:
  selector: "a[class*='next'], button[class*='next'], [aria-label*='suivant'], a:has-text('Suivant'), a:has-text('>')"
  wait_for:
    selector: "[class*='job-item'], [class*='offer-item'], article[class*='job']"
    state: visible
    timeout: 15000
max_pages: 5
on_no_more:
  - action: log
    message: "Fin de la pagination Cadre Emploi"
```
