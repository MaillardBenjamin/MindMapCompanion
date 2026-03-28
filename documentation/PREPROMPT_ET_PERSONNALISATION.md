# Preprompt et personnalisation des agents

## Contexte injecté automatiquement

À chaque exécution d’un agent configurable, le backend :

1. **Préfixe un bloc « Contexte d’exécution »** (preprompt) au prompt, contenant :
   - **Date** du jour (ex. « 7 février 2026 »)
   - **Heure** (ex. « 10h40 »)
   - **Langue de réponse** (par défaut : `fr`) — avec consigne de rédiger dans cette langue
   - **Comment s'adresser** : tutoiement (tu) ou vouvoiement (vous) si fourni
   - **Prénom** du destinataire (si fourni dans les options)
   - **Ton** souhaité (si fourni : formel, amical, etc.)

2. **Injecte des variables** dans le template du prompt, utilisables via `{{variable}}` :
   - `{{current_date}}` — date du jour en français
   - `{{current_year}}` — année
   - `{{current_time}}` — heure courante (ex. 10h40)
   - `{{langue}}` — langue de réponse (défaut : fr)
   - `{{adresse}}` — façon de s'adresser : `tu` ou `vous` (si passé dans les options)
   - `{{prenom}}` — prénom (si passé dans les options)
   - `{{ton}}` — ton (si passé dans les options)

Toute autre option envoyée dans `options` / `agent_options` est aussi disponible en `{{nom_option}}` dans le prompt.

## Paramètres de personnalisation

Lors de la configuration d’un trigger (ou de l’appel API d’exécution), vous pouvez passer :

| Paramètre                 | Clé dans `agent_options` | Description                                                                              |
| ------------------------- | ------------------------ | ---------------------------------------------------------------------------------------- |
| **Langue de réponse**     | `langue`                 | Code langue : `fr`, `en`, `es`, `de`. Par défaut `fr`.                                   |
| **Comment s'adresser**    | `adresse`                | `tu` (tutoiement) ou `vous` (vouvoiement).                                               |
| **Prénom**                | `prenom`                 | Prénom du destinataire (ex. « Benjamin »). Utilisé dans le preprompt et en `{{prenom}}`. |
| **Ton / façon de parler** | `ton`                    | Ton de la réponse : `formel`, `amical`, `neutre`, `professionnel`, `bienveillant`, etc.  |

Ces préférences se configurent **une seule fois** dans le menu **Paramètres** du site (section « Réponses des agents »). Elles sont enregistrées **en base de données** (table `users`, colonnes `agent_langue`, `agent_adresse`, `agent_prenom`, `agent_ton`) pour l’utilisateur connecté. Elles s’appliquent à tous les agents ; inutile de les renseigner dans chaque trigger.

## Exemple de preprompt généré

```
[Contexte d'exécution]
- Date : 7 février 2026
- Heure : 10h40
- Langue de réponse : fr — rédiger systématiquement dans cette langue.
- S'adresser au destinataire avec : tutoiement (tu).
- Prénom du destinataire : Benjamin
- Ton souhaité : amical

```

Puis le contenu du prompt template de l’agent (avec remplacement de `{{input_text}}`, `{{current_date}}`, etc.).

## API

Lors d’un appel d’exécution d’agent (ou de trigger), les options sont transmises dans le body :

- **POST** `/api/configurable-agents/{id}/execute`  
  Body : `{ "input_text": "...", "options": { "prenom": "Benjamin", "ton": "amical", "langue": "fr" } }`

- **POST** `/api/triggers/{id}/execute`  
  Body : `{ "input_text": "...", "agent_options": { "prenom": "Benjamin", "ton": "amical", "langue": "fr" } }`  
  (pour un trigger de type agent, `agent_options` est fusionné avec la config enregistrée du trigger.)

## Utilisation dans un prompt template (fichier .md d’agent)

Vous pouvez écrire dans la section **Prompt Template** par exemple :

```markdown
Bonjour {{prenom}},

La date du jour est le {{current_date}} ({{current_time}}).
Rédige ta réponse en {{langue}}, avec un ton {{ton}}.

Thème : {{input_text}}
```

Si `prenom` ou `ton` ne sont pas fournis, les lignes correspondantes peuvent être adaptées par l’agent ou rester vides selon la logique du template.
