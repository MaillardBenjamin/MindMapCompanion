---
name: Cadre Emploi Scraper (Browser-Use)
site_url: https://www.cadremploi.fr/emploi/liste_offres
executor_type: browser-use
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
  timeout: 30000
  navigation_timeout: 30000
credentials:
  email_env: null
  password_env: null
---

# Instructions pour Browser-Use avec Ollama

Conversion des étapes Playwright du scraper Cadre Emploi en instructions en langage naturel.

## Objectif

Même flux que le scraper Playwright : construire l’URL (motscles, reg, tyc, salary) → aller sur la page → accepter les cookies (iframe) → cliquer Rechercher → extraire les liens résultats → pour chaque offre (nouvelles uniquement, max 10) ouvrir la page détail et extraire tous les champs.

## Instructions détaillées (équivalent des étapes Playwright)

1. **Navigation initiale (équivalent : action goto)**
   - Va sur : `https://www.cadremploi.fr/emploi/liste_offres?motscles={{search.motscles}}&reg={{search.reg}}&tyc={{search.tyc}}&salary={{search.salary_min}}`
   - Remplace les espaces dans les mots-clés par `+`. Utilise les paramètres fournis : motscles, reg, tyc, salary_min.
   - Attends que le corps de la page soit visible.

2. **Cookies – iframe (équivalent : click_in_iframe #appconsent, bouton TOUT ACCEPTER)**
   - Une bannière de consentement peut être dans un iframe (ex. conteneur #appconsent).
   - Cherche dans la page ou dans un iframe un bouton dont le texte est **« TOUT ACCEPTER »** et clique dessus.
   - Si tu ne trouves pas ce bouton, cherche « Accepter », « J’accepte », « Tout accepter ».
   - Si rien n’apparaît ou pas d’iframe, passe à l’étape suivante.

3. **Lancer la recherche (équivalent : click button "Rechercher")**
   - Clique sur le bouton dont le texte est **« Rechercher »**.
   - Attends que les résultats apparaissent (zone de résultats, liens contenant « offre » ou « detail_offre » ou « /emploi/offre/ »).

4. **Scroll et chargement des liens**
   - Fais défiler la page vers le bas pour charger tous les liens d’offres.
   - Attends que des liens d’offres soient visibles (URLs contenant `offreId`, `detail_offre` ou `/emploi/offre/`).

5. **Extraction de la liste de résultats (équivalent : extract_list sur main / #searchDiv)**
   - Dans la zone principale (main ou #searchDiv), repère tous les liens d’offres : `a[href*='offreId']`, `a[href*='detail_offre']`, `a[href*='/emploi/offre/']`.
   - Pour chaque lien/ carte d’offre, extrais dès que possible :
     - **id** : depuis l’URL (paramètre `offreId` ou `offreid`), obligatoire
     - **title** : texte du lien ou titre de l’offre, obligatoire
     - **url** : href du lien en URL absolue (https://www.cadremploi.fr/...)
     - **company** : nom de l’entreprise (classe contenant company, employer, enterprise)
     - **location** : lieu (classe contenant location, place, city)
     - **salary** : salaire si affiché
     - **contract_type** : type de contrat si affiché
     - **description** : courte description si visible
     - **publish_date** : date si visible
   - **Important** : ignore les offres dont l’id est déjà dans la liste des offres existantes (existing_offer_ids dans le contexte).
   - Stocke cette liste comme « liens d’offres » pour l’étape suivante.

6. **Détail de chaque offre (équivalent : for_each sur offer_links, limit 10, skip_existing)**
   - Prends au maximum **10** offres parmi les liens extraits (en excluant celles déjà existantes).
   - Pour chaque offre :
     - Va sur l’URL de l’offre (`{{offer.url}}`).
     - Attends que le titre principal (h1) soit visible.
     - Sur cette page détail, extrais :
       - **title** : h1
       - **company** : nom de l’entreprise (classe company/enterprise ou lien entreprise ou h3)
       - **location** : lieu
       - **salary** : si affiché
       - **contract_type** : si affiché
       - **publish_date** : si affiché
       - **description** : bloc description / content / detail
       - **missions** : section « Quelles sont les missions » (titre h2 puis contenu suivant)
       - **profil_ideal** : section « Quel est le profil idéal » (titre h2 puis contenu suivant)
       - **informations_complementaires** : section « Informations complémentaires » (titre h2 puis contenu suivant)
   - Fusionne ces champs avec les données déjà extraites pour cette offre (id, url, etc.) et ajoute la source `cadre-emploi` et la date de scraping.

## Format de sortie

Retourne un JSON avec la structure suivante :

```json
{
  "offers": [
    {
      "id": "12345",
      "title": "Développeur Full Stack",
      "company": "Entreprise XYZ",
      "location": "Paris, Île-de-France",
      "url": "https://www.cadremploi.fr/emploi/offre/12345",
      "description": "Description courte de l'offre...",
      "salary": "45000-55000 EUR",
      "contract_type": "CDI",
      "publish_date": "2026-02-05",
      "requirements": ["Python", "React", "PostgreSQL"],
      "source": "cadre-emploi"
    }
  ]
}
```

## Notes importantes

- Ignore les offres dont l'ID est déjà dans la liste des offres existantes (fournie dans le contexte)
- Si un élément n'est pas trouvé, mets une valeur par défaut (chaîne vide ou null)
- Les URLs doivent être absolues (commencer par https://)
- Nettoie les espaces superflus dans les textes extraits
- Si tu rencontres une erreur (popup, CAPTCHA, etc.), essaie de la contourner ou note-la dans les logs
