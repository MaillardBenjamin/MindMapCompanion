"""
Parser pour les fichiers .md de configuration des agents configurables.

Format attendu :
---
name: Nom de l'agent
slug: slug-de-l-agent
description: Description de l'agent
persona: Rôle et style de l'agent
---

# Prompt Template

{{input_text}}

# Output Schema

```json
{
  "type": "object",
  "properties": {
    "field": "string"
  }
}
```

# Tools

- tool_id_1
- tool_id_2

# MCP Servers

- server_name_1
- server_name_2

# Instructions

Instructions additionnelles pour l'agent...
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentConfigParser:
    """Parse les fichiers .md de configuration d'agents"""
    
    @staticmethod
    def parse_markdown(markdown_content: str) -> Dict[str, Any]:
        """
        Parse le contenu markdown et extrait la configuration de l'agent.
        
        Args:
            markdown_content: Contenu du fichier .md
            
        Returns:
            Dictionnaire avec les clés: name, slug, description, persona, prompt_template,
            output_schema, tools, mcp_servers, instructions
        """
        config = {
            "name": "",
            "slug": "",
            "description": "",
            "persona": "",
            "prompt_template": "",
            "output_schema": None,
            "input_schema": None,  # Schéma pour les champs du formulaire
            "tools": [],
            "mcp_servers": [],
            "instructions": "",
            # Configuration des scrapers (pour job-matcher et autres agents de scraping)
            "scrapers": [],
            "storage": None,
            "scoring": None,
        }
        
        # Frontmatter YAML:
        # - On attend un bloc en tête de fichier: `--- ... ---`
        # - On utilise `pyyaml` si disponible (support structures complexes), sinon fallback simple
        # - Le contenu après le frontmatter est parsé par sections Markdown
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', markdown_content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            # Extraire les champs du frontmatter
            config.update(AgentConfigParser._parse_frontmatter(frontmatter))
            # Enlever le frontmatter du contenu
            markdown_content = markdown_content[frontmatter_match.end():]
        
        # Parsing des sections:
        # Convention: sections nommées (H1/H2) comme "Prompt Template", "Output Schema", "Tools", etc.
        # IMPORTANT: les sous-sections H2 qui ne sont pas dans `major_sections` restent rattachées
        # à la section courante (comportement voulu pour ne pas perdre du contexte).
        sections = AgentConfigParser._parse_sections(markdown_content)
        
        # Extraire le input schema (pour les formulaires)
        if "Input Schema" in sections:
            config["input_schema"] = AgentConfigParser._parse_json_schema(sections["Input Schema"])
        elif "input_schema" in sections:
            config["input_schema"] = AgentConfigParser._parse_json_schema(sections["input_schema"])
        
        # Extraire le prompt template
        if "Prompt Template" in sections:
            config["prompt_template"] = sections["Prompt Template"].strip()
        elif "prompt_template" in sections:
            config["prompt_template"] = sections["prompt_template"].strip()
        
        # Extraire le schéma de sortie
        if "Output Schema" in sections:
            schema_text = sections["Output Schema"].strip()
            config["output_schema"] = AgentConfigParser._parse_json_schema(schema_text)
        elif "output_schema" in sections:
            schema_text = sections["output_schema"].strip()
            config["output_schema"] = AgentConfigParser._parse_json_schema(schema_text)
        
        # Extraire les outils
        if "Tools" in sections:
            config["tools"] = AgentConfigParser._parse_list(sections["Tools"])
        elif "tools" in sections:
            config["tools"] = AgentConfigParser._parse_list(sections["tools"])
        
        # Extraire les serveurs MCP
        if "MCP Servers" in sections:
            config["mcp_servers"] = AgentConfigParser._parse_list(sections["MCP Servers"])
        elif "mcp_servers" in sections:
            config["mcp_servers"] = AgentConfigParser._parse_list(sections["mcp_servers"])
        
        # Extraire les instructions
        if "Instructions" in sections:
            config["instructions"] = sections["Instructions"].strip()
        elif "instructions" in sections:
            config["instructions"] = sections["instructions"].strip()
        
        # Si le prompt template est vide, utiliser tout le contenu restant
        if not config["prompt_template"] and markdown_content.strip():
            config["prompt_template"] = markdown_content.strip()
        
        return config
    
    @staticmethod
    def _parse_frontmatter(frontmatter: str) -> Dict[str, Any]:
        """Parse le frontmatter YAML"""
        try:
            import yaml
            # Parser le YAML complet pour gérer les structures complexes
            result = yaml.safe_load(frontmatter) or {}
            
            # Si c'est une liste (cas spécial), convertir en dict
            if isinstance(result, list):
                result = {str(i): item for i, item in enumerate(result)}
            
            # Extraction des mcp_servers si présent sous forme de liste/objet
            if "mcp_servers" in result:
                mcp_servers = result["mcp_servers"]
                # Si c'est une liste d'objets, extraire les noms
                if isinstance(mcp_servers, list):
                    # Extraire les noms si ce sont des dicts avec "name"
                    server_names = [
                        server["name"] if isinstance(server, dict) and "name" in server
                        else server if isinstance(server, str)
                        else str(server)
                        for server in mcp_servers
                    ]
                    result["mcp_servers"] = server_names
                    # Stocker aussi la config complète pour référence future
                    result["_mcp_servers_config"] = mcp_servers
            
            # Extraction des scrapers (pour agents de scraping)
            if "scrapers" in result and isinstance(result["scrapers"], list):
                # Stocker la config complète des scrapers
                result["_scrapers_config"] = result["scrapers"]
                # Extraire les chemins si ce sont des dicts avec "path"
                scraper_paths = []
                for scraper in result["scrapers"]:
                    if isinstance(scraper, dict):
                        if scraper.get("enabled", True):  # Ignorer les scrapers désactivés
                            scraper_paths.append(scraper.get("path", ""))
                    elif isinstance(scraper, str):
                        scraper_paths.append(scraper)
                result["scrapers"] = scraper_paths
            
            # Storage et scoring sont gardés tels quels (dictionnaires)
            # Ils sont déjà correctement extraits par yaml.safe_load
            
            return result
        except ImportError:
            # Fallback si PyYAML n'est pas disponible
            result = {}
            for line in frontmatter.split('\n'):
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    result[key] = value
            return result
        except Exception as e:
            logger.warning(f"Erreur lors du parsing YAML du frontmatter: {e}")
            # Fallback simple
            result = {}
            for line in frontmatter.split('\n'):
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    result[key] = value
            return result
    
    @staticmethod
    def _parse_sections(content: str) -> Dict[str, str]:
        """Parse les sections markdown (titre H1/H2)"""
        sections = {}
        current_section = None
        current_content = []
        
        # Sections majeures qui marquent la fin d'une section précédente
        major_sections = ["Input Schema", "Output Schema", "Tools", "MCP Servers", "Instructions"]
        
        lines = content.split('\n')
        for line in lines:
            # Détecter les titres H1 ou H2
            h1_match = re.match(r'^# (.+)$', line)
            h2_match = re.match(r'^## (.+)$', line)
            
            if h1_match:
                section_name = h1_match.group(1)
                # Sauvegarder la section précédente
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                # Nouvelle section
                current_section = section_name
                current_content = []
            elif h2_match:
                section_name = h2_match.group(1)
                # Sauvegarder la section précédente seulement si c'est une section majeure
                # Sinon, continuer à collecter dans la section actuelle (pour les sous-sections)
                if current_section and section_name in major_sections:
                    sections[current_section] = '\n'.join(current_content).strip()
                    current_section = section_name
                    current_content = []
                elif not current_section:
                    # Si pas de section en cours, créer une nouvelle section
                    current_section = section_name
                    current_content = []
                else:
                    # C'est une sous-section, continuer à collecter dans la section actuelle
                    current_content.append(line)
            elif current_section:
                current_content.append(line)
        
        # Sauvegarder la dernière section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    @staticmethod
    def _parse_json_schema(text: str) -> Optional[Dict[str, Any]]:
        """Parse un schéma JSON depuis un bloc de code markdown"""
        # Chercher un bloc de code JSON
        json_match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Essayer sans le préfixe json
            json_match = re.search(r'```\n(.*?)\n```', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Essayer de parser directement le texte
                json_text = text.strip()
        
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Erreur lors du parsing du schéma JSON: {e}")
            return None
    
    @staticmethod
    def _parse_list(text: str) -> List[str]:
        """Parse une liste (markdown bullet list ou comma-separated)"""
        items = []
        
        # Parser les listes markdown (bullet points)
        for line in text.split('\n'):
            line = line.strip()
            # Détecter les bullet points (-, *, •)
            bullet_match = re.match(r'^[-*•]\s+(.+)$', line)
            if bullet_match:
                item_text = bullet_match.group(1).strip()
                # Extraire le nom de l'outil s'il est entre backticks
                # Format: `tool_name` - Description... ou `tool_name`: Description...
                backtick_match = re.match(r'^`([^`]+)`', item_text)
                if backtick_match:
                    items.append(backtick_match.group(1).strip())
                else:
                    # Prendre juste le premier mot avant un tiret ou deux-points
                    first_word_match = re.match(r'^(\S+)(?:\s*[-:].+)?$', item_text)
                    if first_word_match:
                        items.append(first_word_match.group(1).strip())
                    else:
                        items.append(item_text)
            # Détecter les numéros (1., 2., etc.)
            numbered_match = re.match(r'^\d+\.\s+(.+)$', line)
            if numbered_match:
                item_text = numbered_match.group(1).strip()
                # Même logique pour les noms entre backticks
                backtick_match = re.match(r'^`([^`]+)`', item_text)
                if backtick_match:
                    items.append(backtick_match.group(1).strip())
                else:
                    first_word_match = re.match(r'^(\S+)(?:\s*[-:].+)?$', item_text)
                    if first_word_match:
                        items.append(first_word_match.group(1).strip())
                    else:
                        items.append(item_text)
        
        # Si pas de liste markdown trouvée, essayer comma-separated
        if not items:
            items = [item.strip() for item in text.split(',') if item.strip()]
        
        return items
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valide la configuration parsée.
        
        Returns:
            (is_valid, error_message)
        """
        if not config.get("name"):
            return False, "Le nom de l'agent est requis"
        
        if not config.get("slug"):
            return False, "Le slug de l'agent est requis"
        
        if not config.get("prompt_template"):
            return False, "Le template de prompt est requis"
        
        # Vérifier que le prompt template contient {{input_text}}
        if "{{input_text}}" not in config.get("prompt_template", ""):
            logger.warning("Le prompt template ne contient pas {{input_text}}")
        
        return True, None
    
    @staticmethod
    def render_prompt(template: str, input_text: str, **kwargs) -> str:
        """
        Rend le template de prompt en remplaçant {{input_text}} et autres variables.
        
        Args:
            template: Template de prompt avec {{input_text}}
            input_text: Texte à injecter
            **kwargs: Autres variables à remplacer dans le template
            
        Returns:
            Prompt rendu
        """
        prompt = template.replace("{{input_text}}", input_text)
        
        # Remplacer les autres variables
        import re
        for key, value in kwargs.items():
            if value:  # Ne remplacer que si la valeur existe et n'est pas vide
                prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
            else:
                # Supprimer les lignes contenant la variable vide (avec le label avant)
                # Pattern pour trouver les lignes qui contiennent la variable (avec label optionnel avant)
                # Ex: "Label : {{variable}}" ou juste "{{variable}}"
                pattern = rf'^.*?{{{{{{key}}}}}}.*?$'
                prompt = re.sub(pattern, '', prompt, flags=re.MULTILINE)
        
        # Nettoyer les variables non remplacées (optionnelles) - lignes qui contiennent encore {{variable}}
        prompt = re.sub(r'^.*?{{{\w+}}}.*?$', '', prompt, flags=re.MULTILINE)
        # Nettoyer les lignes vides multiples
        prompt = re.sub(r'\n\s*\n\s*\n', '\n\n', prompt)
        
        return prompt.strip()
