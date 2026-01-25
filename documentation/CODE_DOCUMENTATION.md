# Guide de Documentation du Code

Ce document décrit les standards de documentation du code pour le projet Personal Assistant.

## 📋 Standards de documentation

### Python (Backend)

#### Style : Google Docstrings

Utilisez le format Google pour les docstrings Python :

```python
def function_name(param1: str, param2: int) -> dict:
    """
    Description courte en une ligne.
    
    Description détaillée si nécessaire, sur plusieurs lignes.
    Explique ce que fait la fonction, pourquoi elle existe,
    et comment elle fonctionne.
    
    Args:
        param1: Description du premier paramètre.
        param2: Description du second paramètre.
    
    Returns:
        Description de ce qui est retourné.
        Format: {"key": "value"}
    
    Raises:
        ValueError: Quand param1 est vide.
        HTTPException: Quand l'utilisateur n'est pas autorisé.
    
    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        {"key": "value"}
    
    Note:
        Informations supplémentaires importantes.
    """
    pass
```

#### Classes

```python
class MyClass:
    """
    Description courte de la classe.
    
    Description détaillée de la classe, son rôle,
    et comment elle s'intègre dans l'architecture.
    
    Attributes:
        attr1: Description de l'attribut.
        attr2: Description de l'attribut.
    
    Example:
        >>> obj = MyClass()
        >>> obj.method()
    """
    
    def __init__(self, param: str):
        """
        Initialise une instance de MyClass.
        
        Args:
            param: Description du paramètre.
        """
        self.attr1 = param
```

#### Modules

```python
"""
Nom du module.

Description du rôle du module dans l'application.
Liste des fonctionnalités principales.

Example:
    Utilisation basique du module.
"""
```

### TypeScript/React (Frontend)

#### Fonctions

```typescript
/**
 * Description courte de la fonction.
 * 
 * Description détaillée si nécessaire.
 * 
 * @param param1 - Description du paramètre
 * @param param2 - Description du paramètre
 * @returns Description de la valeur retournée
 * 
 * @example
 * ```ts
 * const result = functionName("test", 42);
 * console.log(result);
 * ```
 */
function functionName(param1: string, param2: number): object {
  return {};
}
```

#### Composants React

```typescript
/**
 * Composant pour afficher [description].
 * 
 * @param props - Propriétés du composant
 * @param props.title - Titre à afficher
 * @param props.onClick - Callback appelé au clic
 * 
 * @example
 * ```tsx
 * <MyComponent 
 *   title="Mon titre" 
 *   onClick={() => console.log("clicked")} 
 * />
 * ```
 */
interface MyComponentProps {
  title: string;
  onClick: () => void;
}

export const MyComponent: React.FC<MyComponentProps> = ({ title, onClick }) => {
  return <div onClick={onClick}>{title}</div>;
};
```

## 📝 Niveaux de documentation

### 1. Documentation publique (API)

**Où** : Toutes les fonctions/classes exposées publiquement
- Routes API (`app/api/routes/`)
- Services publics (`app/services/`)
- CRUD (`app/crud/`)
- Composants React exportés

**Contenu minimum** :
- Description courte
- Paramètres avec types
- Retour avec type
- Exceptions possibles

### 2. Documentation interne

**Où** : Fonctions/classes utilisées en interne
- Fonctions privées (`_function_name`)
- Helpers internes
- Utilitaires

**Contenu minimum** :
- Description courte
- Paramètres principaux

### 3. Documentation complexe

**Où** : Algorithmes complexes, logique métier importante
- Parsing de données
- Transformations complexes
- Logique de validation

**Contenu** :
- Description détaillée
- Algorithme expliqué
- Exemples
- Cas limites

## ✅ Checklist de documentation

Pour chaque fonction/classe :

- [ ] Docstring présente
- [ ] Description claire et concise
- [ ] Paramètres documentés avec types
- [ ] Retour documenté avec type
- [ ] Exceptions documentées (si applicables)
- [ ] Exemple d'utilisation (si complexe)
- [ ] Notes importantes (si nécessaire)

## 📚 Exemples de bonne documentation

### Exemple 1 : Route API

```python
@router.post("/api/triggers", response_model=TriggerResponse)
def create_trigger(
    trigger: TriggerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> TriggerResponse:
    """
    Crée un nouveau trigger associé à un nœud.
    
    Le trigger permet d'automatiser des actions (exécution d'agents,
    envoi d'emails) selon différents types de déclencheurs (cron,
    date_reached, email_received, etc.).
    
    Args:
        trigger: Données du trigger à créer (node_id, trigger_type, config).
        current_user: Utilisateur authentifié (injecté par FastAPI).
        db: Session de base de données (injectée par FastAPI).
    
    Returns:
        TriggerResponse: Le trigger créé avec son ID.
    
    Raises:
        HTTPException: 
            - 404 si le nœud n'existe pas ou n'appartient pas à l'utilisateur.
            - 400 si la configuration du trigger est invalide.
    
    Example:
        >>> trigger_data = TriggerCreate(
        ...     node_id="123e4567-e89b-12d3-a456-426614174000",
        ...     trigger_type="cron",
        ...     config={"cron_expression": "0 9 * * 1,3,5"}
        ... )
        >>> result = create_trigger(trigger_data, user, db)
        >>> print(result.id)
    """
    pass
```

### Exemple 2 : Service complexe

```python
class ConfigurableAgentService:
    """
    Service pour gérer et exécuter les agents IA configurables.
    
    Ce service permet de :
    - Créer des agents Agno depuis une configuration Markdown
    - Exécuter des agents avec des inputs personnalisés
    - Parser les sorties Markdown selon un schéma JSON
    - Logger toutes les exécutions pour traçabilité
    
    Les agents sont configurés via des fichiers Markdown avec :
    - Un persona (rôle de l'agent)
    - Des instructions détaillées
    - Un schéma de sortie JSON
    - Des outils disponibles (web_search, etc.)
    
    Example:
        >>> service = ConfigurableAgentService()
        >>> result = service.execute_agent(
        ...     db=session,
        ...     agent_id=1,
        ...     user_id=1,
        ...     input_text="Recherche actualités IA"
        ... )
        >>> print(result["output_raw"])
    """
    
    def execute_agent(
        self,
        db: Session,
        agent_id: int,
        user_id: int,
        input_text: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Exécute un agent configurable avec un texte d'entrée.
        
        Le processus d'exécution :
        1. Charge la configuration de l'agent depuis la DB
        2. Crée un agent Agno avec le modèle OpenAI
        3. Configure les outils demandés (web_search, etc.)
        4. Exécute l'agent avec le texte d'entrée
        5. Parse la sortie Markdown selon le schéma
        6. Log l'exécution dans agent_execution_logs
        
        Args:
            db: Session de base de données.
            agent_id: ID de l'agent configurable à exécuter.
            user_id: ID de l'utilisateur qui exécute l'agent.
            input_text: Texte d'entrée pour l'agent.
            options: Options supplémentaires (non utilisé actuellement).
        
        Returns:
            Dict contenant :
            - output_raw: Sortie Markdown brute de l'agent
            - output_parsed: Sortie parsée selon le schéma (JSON)
            - execution_time_ms: Temps d'exécution en millisecondes
            - prompt_used: Prompt complet utilisé pour l'agent
            - input_text: Texte d'entrée utilisé
        
        Raises:
            ValueError: Si l'agent n'existe pas ou n'appartient pas à l'utilisateur.
            RuntimeError: Si l'exécution de l'agent échoue.
        
        Note:
            Les exécutions sont loggées dans la table agent_execution_logs
            pour traçabilité et analyse.
        """
        pass
```

### Exemple 3 : Fonction utilitaire

```python
def parse_cron_expression(cron_expr: str) -> dict:
    """
    Parse une expression cron en paramètres pour APScheduler.
    
    Format attendu: "minute heure * * jours"
    - minute: 0-59 ou *
    - heure: 0-23 ou *
    - jours: 0-6 (0=dimanche) ou * ou liste comme "1,3,5"
    
    Args:
        cron_expr: Expression cron au format "minute heure * * jours".
    
    Returns:
        Dict avec les clés 'minute', 'hour', 'day_of_week' si spécifiés.
        Exemple: {"minute": "0", "hour": "9", "day_of_week": "1,3,5"}
    
    Raises:
        ValueError: Si l'expression cron est invalide.
    
    Example:
        >>> params = parse_cron_expression("0 9 * * 1,3,5")
        >>> print(params)
        {"minute": "0", "hour": "9", "day_of_week": "1,3,5"}
    """
    pass
```

## 🔍 Outils de documentation

### Génération de documentation

**Sphinx** (Python) :
```bash
pip install sphinx sphinx-rtd-theme
sphinx-quickstart docs/
```

**TypeDoc** (TypeScript) :
```bash
npm install --save-dev typedoc
typedoc --out docs src/
```

### Vérification

**pydocstyle** (Python) :
```bash
pip install pydocstyle
pydocstyle app/
```

**ESLint** (TypeScript) :
```json
{
  "rules": {
    "require-jsdoc": "warn"
  }
}
```

## 📖 Références

- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [PEP 257 - Docstring Conventions](https://www.python.org/dev/peps/pep-0257/)
- [TypeScript JSDoc](https://www.typescriptlang.org/docs/handbook/jsdoc-supported-types.html)

## 🎯 Objectifs

La documentation du code doit permettre à un développeur de :
1. **Comprendre** ce que fait le code sans le lire
2. **Utiliser** l'API sans regarder l'implémentation
3. **Maintenir** le code en comprenant les intentions
4. **Éviter** les erreurs en connaissant les contraintes

---

**Note** : Ce guide est un standard à suivre pour tout nouveau code. Le code existant sera progressivement documenté selon ces standards.
