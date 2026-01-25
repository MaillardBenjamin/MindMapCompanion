---
name: Indeed Scraper
site_url: https://fr.indeed.com
storage:
  base_dir: data/job_offers/indeed
  subdir_pattern: "{date}"
  file_pattern: "{title_slug}-{id}.md"
  archive_dir: data/job_offers/archive/indeed
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
  # Indeed ne nécessite pas d'authentification pour les recherches de base
  email_env: null
  password_env: null
anti_bot:
  enabled: true
  random_delays:
    min: 3000
    max: 7000
    between_actions: true
  mouse_movements: false
  human_typing: true
rate_limiting:
  enabled: true
  requests_per_minute: 4
  delay_between_requests: 15000
error_handling:
  retry_on_failure: 3
  retry_delay: 10000
---

# Instructions Playwright pour Indeed

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
selector: "#onetrust-consent-sdk, [class*='cookie'], [id*='cookie'], [class*='privacy']"
strategy: accept
fallback:
  - action: click
    selector: "#onetrust-accept-btn-handler, button[id*='accept'], button:has-text('Accepter'), button:has-text('Accept')"
    timeout: 5000
  - action: wait
    timeout: 2000
```

### Étape 3: Fermeture des popups éventuels
```yaml
action: handle_popup
type: modal
selector: "[class*='popup'], [class*='modal'], [role='dialog']"
strategy: close
fallback:
  - action: press
    key: Escape
  - action: wait
    timeout: 1000
```

## Recherche

### Étape 4: Remplissage des mots-clés
```yaml
action: fill
selector: "input#text-input-what, input[name='q'], input[id*='what'], input[placeholder*='métier']"
value: "{{search.keywords}}"
options:
  clear: true
  timeout: 5000
```

### Étape 5: Remplissage de la localisation
```yaml
action: fill
selector: "input#text-input-where, input[name='l'], input[id*='where'], input[placeholder*='lieu']"
value: "{{search.location}}"
options:
  clear: true
  timeout: 5000
```

### Étape 6: Lancement de la recherche
```yaml
action: click
selector: "button[type='submit'], button:has-text('Rechercher'), button:has-text('Trouver')"
wait_for:
  selector: "[class*='job_seen_beacon'], [class*='resultContent'], [class*='jobsearch-ResultsList'], .job_seen_beacon"
  state: visible
  timeout: 20000
```

### Étape 7: Attente du chargement complet
```yaml
action: wait
timeout: 3000
```

## Extraction

### Étape 8: Scroll pour charger le contenu
```yaml
action: scroll
direction: down
amount: 1000
wait_for:
  selector: "[class*='job_seen_beacon'], .job_seen_beacon"
  state: visible
  timeout: 5000
```

### Étape 9: Extraction des offres
```yaml
action: extract_list
container_selector: "[class*='jobsearch-ResultsList'], #mosaic-jobResults, main"
item_selector: "[class*='job_seen_beacon'], .job_seen_beacon, [class*='resultContent'], li[class*='result']"
fields:
  - name: title
    selector: "h2[class*='jobTitle'] a, a[class*='jcs-JobTitle'], [class*='title'] a, h2 a"
    type: text
    required: true
    transform: trim
  - name: company
    selector: "[class*='companyName'], [data-testid='company-name'], span[class*='company']"
    type: text
    required: true
    transform: trim
  - name: location
    selector: "[class*='companyLocation'], [data-testid='text-location'], [class*='location']"
    type: text
    fallback: "Non spécifié"
    transform: trim
  - name: salary
    selector: "[class*='salary-snippet'], [class*='salaryText'], [class*='salary'], [data-testid*='salary']"
    type: text
    optional: true
    transform: trim
  - name: description
    selector: "[class*='job-snippet'], [class*='snippetText'], ul[class*='css'], [class*='summary']"
    type: text
    optional: true
    transform: trim
  - name: url
    selector: "h2[class*='jobTitle'] a, a[class*='jcs-JobTitle'], [class*='title'] a, h2 a"
    type: attribute
    attribute: href
    transform: absolute_url
  - name: source_id
    selector: "[data-jk], [data-job-id]"
    type: attribute
    attribute: data-jk
    optional: true
  - name: publish_date
    selector: "[class*='date'], span[class*='visually-hidden']:has-text('jour'), [class*='posted']"
    type: text
    optional: true
    transform: trim
  - name: contract_type
    selector: "[class*='metadata']:has-text('CDI'), [class*='metadata']:has-text('CDD'), [class*='attribute_snippet']"
    type: text
    optional: true
    transform: trim
metadata:
  source: indeed
  scraped_at: "{{timestamp}}"
  search_keywords: "{{search.keywords}}"
  search_location: "{{search.location}}"
```

## Pagination

### Étape 10: Navigation vers les pages suivantes
```yaml
action: paginate
strategy: click_next
next_button:
  selector: "a[data-testid='pagination-page-next'], a[aria-label*='Suivant'], nav[role='navigation'] a:last-child, a:has-text('Suivant')"
  wait_for:
    selector: "[class*='job_seen_beacon'], .job_seen_beacon"
    state: visible
    timeout: 20000
max_pages: 5
on_no_more:
  - action: log
    message: "Fin de la pagination Indeed"
```

### Étape 11: Scroll additionnel après chaque page
```yaml
action: scroll
direction: bottom
wait_for:
  selector: "[class*='job_seen_beacon']"
  state: visible
  timeout: 5000
```
