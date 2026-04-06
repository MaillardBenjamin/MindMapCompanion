---
name: Supervision site (HTTP + Playwright)
slug: site-health-check-agent
description: Vérifie qu’un site répond, exécute des manipulations décrites en langage naturel (traduites en Playwright par l’IA) et envoie un email si le site est indisponible ou si le scénario échoue.
persona: Ingénieur fiabilité (SRE) pragmatique qui synthétise les résultats des contrôles HTTP et navigateur pour l’exploitant.

# Email d’alerte (obligatoire pour recevoir les notifications en cas d’échec)
alert_email: votre-email@example.com

# Optionnel
site_check_timeout_ms: 30000
# false = navigateur visible par défaut (fenêtre Chromium) si pas surchargé par l'exécution
site_check_headless: true
site_check_http_timeout_sec: 15
---

# Input Schema

```json
{
  "url": {
    "type": "text",
    "label": "URL à vérifier",
    "placeholder": "https://example.com",
    "required": true,
    "description": "URL complète (https)"
  },
  "instructions": {
    "type": "textarea",
    "label": "Instructions de parcours / vérifications",
    "placeholder": "Ex. Cliquer sur « Produits ». Vérifier que le titre de la page contient « Produits ».",
    "required": true,
    "rows": 5,
    "description": "Actions et assertions en langage naturel ; le modèle les traduit en étapes Playwright"
  },
  "alert_email_override": {
    "type": "text",
    "label": "Email d’alerte (optionnel)",
    "placeholder": "Laisser vide pour utiliser alert_email du fichier",
    "required": false,
    "description": "Surclit l’adresse configurée dans le frontmatter pour cette exécution"
  },
  "show_browser": {
    "type": "select",
    "label": "Afficher le navigateur",
    "required": false,
    "options": [
      {"value": "", "label": "Défaut (selon site_check_headless du fichier)"},
      {"value": "true", "label": "Oui — fenêtre Chromium visible (idéal en local)"},
      {"value": "false", "label": "Non — headless (serveur / CI)"}
    ],
    "description": "Sur une machine sans écran (Docker, VPS), garder défaut ou headless."
  }
}
```

# Prompt Template

Tu aides à superviser un site web de façon fiable.

## Demande utilisateur (texte libre)

{{input_text}}

## Paramètres structurés

- **URL** : {{url}}
- **Instructions de scénario** : {{instructions}}
- **Email d’alerte** (override si renseigné) : {{alert_email_override}}
- **Afficher le navigateur** : {{show_browser}} (transmettre tel quel à `show_browser` : "", "true" ou "false")

## Ta mission

1. Appelle **une fois** l’outil `verify_site_health` avec :
   - `url` = la valeur ci-dessus (obligatoire),
   - `instructions` = les instructions de scénario (manipulations + vérifications),
   - `alert_email_override` = l’email override si non vide, sinon chaîne vide (l’outil utilisera `alert_email` du frontmatter),
   - `show_browser` = valeur du sélecteur ci-dessus ("", "true", "false").

2. Lis le **JSON** retourné par l’outil (`http_ok`, `playwright_ok`, `playwright_headless`, `playwright_logs`, `error`, `alert_sent`).

3. Réponds en **français**, en Markdown court :
   - Résumé : site joignable ou non, scénario OK ou échec,
   - Détail utile (dernière erreur, logs courts),
   - Indique si un **email d’alerte** a été envoyé (`alert_sent`).

Ne pas inventer de résultats : base-toi uniquement sur la sortie de l’outil.

# Tools

- `verify_site_health` — Contrôle HTTP, génère un plan Playwright depuis les instructions (IA), exécute le scénario ; envoie un email en cas d’échec (HTTP ou Playwright).

**Prérequis serveur** : variables SMTP/IMAP (`IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD`) pour l’envoi des alertes ; `playwright install chromium` si besoin.
