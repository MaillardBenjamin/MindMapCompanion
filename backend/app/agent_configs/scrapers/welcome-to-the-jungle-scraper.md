---
name: Welcome to the Jungle Scraper
site_url: https://www.welcometothejungle.com
storage:
  base_dir: data/job_offers/welcome-to-the-jungle
  subdir_pattern: "{date}"
  file_pattern: "{title_slug}-{id}.md"
  archive_dir: data/job_offers/archive/welcome-to-the-jungle
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
  # WTTJ permet la recherche sans authentification
  email_env: WTTJ_EMAIL
  password_env: WTTJ_PASSWORD
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
  requests_per_minute: 5
  delay_between_requests: 12000
error_handling:
  retry_on_failure: 3
  retry_delay: 5000
---

# Instructions Playwright pour Welcome to the Jungle

## Navigation

### Étape 1: Accès au site
```yaml
action: goto
url: "{{site_url}}/fr/jobs"
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
selector: "[class*='cookie'], [id*='cookie'], [class*='consent'], [data-testid*='cookie']"
strategy: accept
fallback:
  - action: click
    selector: "button:has-text('Accepter'), button:has-text('Accept'), button[class*='accept'], [data-testid*='accept']"
    timeout: 5000
  - action: wait
    timeout: 2000
```

### Étape 3: Fermeture des popups éventuels
```yaml
action: handle_popup
type: modal
selector: "[class*='popup'], [class*='modal'], [role='dialog'], [class*='overlay']"
strategy: close
fallback:
  - action: click
    selector: "button[aria-label='Fermer'], button[aria-label='Close'], [class*='close']"
    timeout: 3000
  - action: press
    key: Escape
```

## Recherche

### Étape 4: Remplissage des mots-clés
```yaml
action: fill
selector: "input[name='query'], input[placeholder*='métier'], input[placeholder*='job'], input[type='search']"
value: "{{search.keywords}}"
options:
  clear: true
  timeout: 5000
```

### Étape 5: Remplissage de la localisation
```yaml
action: fill
selector: "input[name='aroundQuery'], input[placeholder*='lieu'], input[placeholder*='location'], input[name*='location']"
value: "{{search.location}}"
options:
  clear: true
  timeout: 5000
```

### Étape 6: Lancement de la recherche
```yaml
action: click
selector: "button[type='submit'], button:has-text('Rechercher'), form button, [data-testid='search-button']"
wait_for:
  selector: "[class*='job-card'], [class*='offer'], article, [data-testid*='job']"
  state: visible
  timeout: 20000
on_error:
  - action: press
    key: Enter
  - action: wait
    timeout: 5000
```

### Étape 7: Attente du chargement
```yaml
action: wait
timeout: 3000
```

## Extraction

### Étape 8: Scroll pour charger plus d'offres
```yaml
action: scroll
direction: down
amount: 2000
```

### Étape 9: Attente après scroll
```yaml
action: wait
timeout: 2000
```

### Étape 10: Extraction des offres
```yaml
action: extract_list
container_selector: "main, [class*='job-list'], [class*='results'], [role='main']"
item_selector: "[class*='job-card'], article[class*='sc-'], a[href*='/jobs/'], [data-testid*='job-card'], li[class*='sc-']"
fields:
  - name: title
    selector: "h3, h4, [class*='title'], a[class*='title'], span[class*='title']"
    type: text
    required: true
    transform: trim
  - name: company
    selector: "[class*='company'], [class*='organization'], span[class*='name']:first-of-type"
    type: text
    required: true
    transform: trim
  - name: location
    selector: "[class*='location'], [class*='place'], [class*='city'], i[class*='location'] + span"
    type: text
    fallback: "Non spécifié"
    transform: trim
  - name: contract_type
    selector: "[class*='contract'], [class*='type'], span:has-text('CDI'), span:has-text('CDD'), span:has-text('Stage')"
    type: text
    optional: true
    transform: trim
  - name: salary
    selector: "[class*='salary'], [class*='salaire'], [class*='remuneration']"
    type: text
    optional: true
    transform: trim
  - name: description
    selector: "[class*='description'], [class*='excerpt'], [class*='preview'], p"
    type: text
    optional: true
    transform: trim
  - name: url
    selector: "a[href*='/jobs/'], a[href*='/fr/companies/']"
    type: attribute
    attribute: href
    transform: absolute_url
  - name: publish_date
    selector: "[class*='date'], time, [class*='posted'], [class*='published']"
    type: text
    optional: true
    transform: trim
  - name: tags
    selector: "[class*='tag'], [class*='skill'], [class*='badge']"
    type: list
    item_selector: "span, li"
    optional: true
metadata:
  source: welcome-to-the-jungle
  scraped_at: "{{timestamp}}"
  search_keywords: "{{search.keywords}}"
  search_location: "{{search.location}}"
```

## Pagination

### Étape 11: Scroll pour charger plus (infinite scroll)
```yaml
action: paginate
strategy: scroll_load
max_pages: 5
on_no_more:
  - action: log
    message: "Fin du chargement Welcome to the Jungle"
```

### Étape 12: Navigation classique si disponible
```yaml
action: paginate
strategy: click_next
next_button:
  selector: "button:has-text('Voir plus'), button:has-text('Charger plus'), a[rel='next'], [class*='load-more']"
  wait_for:
    selector: "[class*='job-card'], article"
    state: visible
    timeout: 15000
max_pages: 3
on_no_more:
  - action: log
    message: "Plus de pages disponibles"
```
