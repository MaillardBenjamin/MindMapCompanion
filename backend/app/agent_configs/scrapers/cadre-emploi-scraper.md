---
name: Cadre Emploi Scraper
site_url: https://www.cadremploi.fr/emploi/liste_offres
storage:
  base_dir: data/job_offers/cadre-emploi
  subdir_pattern: ""
  file_pattern: "{id}.md"
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
  navigation_timeout: 30000
  wait_until: domcontentloaded
credentials:
  email_env: null
  password_env: null
anti_bot:
  enabled: true
  random_delays:
    min: 200
    max: 600
    between_actions: true
  mouse_movements: false
  human_typing: true
rate_limiting:
  enabled: true
  requests_per_minute: 30
  delay_between_requests: 1000
error_handling:
  retry_on_failure: 3
  retry_delay: 5000
---

# Instructions Playwright pour Cadre Emploi

Flux : construire l’URL (motscles, reg, tyc, salary) → goto → cookies (iframe) → cliquer Rechercher → extraction des liens résultats.

## Navigation

### Étape 1: Accès au site avec URL construite
```yaml
action: goto
url: "{{site_url}}?motscles={{search.motscles}}&reg={{search.reg}}&tyc={{search.tyc}}&salary={{search.salary_min}}"
options:
  wait_until: domcontentloaded
  timeout: 30000
wait_for:
  selector: "body"
  state: visible
  timeout: 10000
```

### Étape 2: Cookies – iframe #appconsent, bouton TOUT ACCEPTER
```yaml
action: click_in_iframe
iframe_selector: "#appconsent iframe"
role: button
name: "TOUT ACCEPTER"
options:
  timeout: 5000
on_error:
  - action: skip
wait_for:
  selector: "[role='combobox']"
  state: visible
  timeout: 8000
```

### Étape 3: Lancer la recherche
```yaml
action: click
role: button
name: "Rechercher"
wait_for:
  selector: "#searchDiv, [class*='result'], main a[href*='/emploi/offre']"
  state: visible
  timeout: 20000
```

## Extraction – liens résultats puis pages détail

### Étape 4: Scroll et attente des liens offres
```yaml
action: scroll
direction: bottom
wait_for:
  selector: "a[href*='offreId'], a[href*='detail_offre'], a[href*='/emploi/offre/']"
  state: visible
  timeout: 15000
```

### Étape 5: Extraire les liens détail_offre (sans cliquer)
# Plusieurs sélecteurs : offreId, detail_offre, /emploi/offre/ - container main ou #searchDiv
```yaml
action: extract_list
container_selector: "main, #searchDiv"
item_selector: "a[href*='offreId'], a[href*='detail_offre'], a[href*='/emploi/offre/']"
append: false
store_as: offer_links
fields:
  - name: id
    selector: "self"
    type: attribute
    attribute: href
    transform: offre_id
  - name: title
    selector: "self"
    type: text
    required: true
    transform: trim
  - name: url
    selector: "self"
    type: attribute
    attribute: href
    transform: absolute_url
  - name: company
    selector: "[class*='company'], [class*='employer'], [class*='enterprise']"
    type: text
    fallback: ""
    transform: trim
  - name: location
    selector: "[class*='location'], [class*='place'], [class*='city']"
    type: text
    fallback: ""
    transform: trim
  - name: salary
    selector: "[class*='salary'], [class*='salaire']"
    type: text
    optional: true
    transform: trim
  - name: contract_type
    selector: "[class*='contract'], [class*='contrat']"
    type: text
    optional: true
    transform: trim
  - name: description
    selector: "[class*='description'], [class*='summary'], p"
    type: text
    optional: true
    transform: trim
  - name: publish_date
    selector: "[class*='date'], time"
    type: text
    optional: true
    transform: trim
metadata:
  source: cadre-emploi
  scraped_at: "{{timestamp}}"
  search_keywords: "{{search.keywords}}"
  search_location: "{{search.location}}"
```

### Étape 6: Ouvrir chaque lien et extraire le détail (nouvelles annonces uniquement)
```yaml
action: for_each
items: offer_links
item_var: offer
limit: 10
skip_existing: true
steps:
  - action: goto
    url: "{{offer.url}}"
    options:
      wait_until: domcontentloaded
      timeout: 15000
  - action: wait_for
    selector: "main h1, h1"
    state: visible
    timeout: 15000
  - action: extract
    append: true
    merge_with_item_var: offer
    fields:
      - name: title
        selector: "h1"
        type: text
        required: true
        transform: trim
      - name: company
        selector: "[class*='company'], [class*='enterprise'], a[href*='/emploi/entreprise'], h3"
        type: text
        fallback: ""
        transform: trim
      - name: location
        selector: "[class*='location'], [class*='place'], [class*='city']"
        type: text
        fallback: ""
        transform: trim
      - name: salary
        selector: "[class*='salary'], [class*='salaire']"
        type: text
        optional: true
        transform: trim
      - name: contract_type
        selector: "[class*='contract'], [class*='contrat']"
        type: text
        optional: true
        transform: trim
      - name: publish_date
        selector: "[class*='date'], time"
        type: text
        optional: true
        transform: trim
      - name: description
        selector: "[class*='description'], [class*='content'], [class*='detail']"
        type: text
        optional: true
        transform: trim
      - name: missions
        selector: "xpath=//h2[contains(.,'Quelles sont les missions')]/following-sibling::*[1]"
        type: text
        optional: true
        transform: trim
      - name: profil_ideal
        selector: "xpath=//h2[contains(.,'Quel est le profil idéal')]/following-sibling::*[1]"
        type: text
        optional: true
        transform: trim
      - name: informations_complementaires
        selector: "xpath=//h2[contains(.,'Informations complémentaires')]/following-sibling::*[1]"
        type: text
        optional: true
        transform: trim
```
