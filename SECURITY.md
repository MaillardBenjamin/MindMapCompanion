# Politique de Sécurité

## 🔒 Signalement de vulnérabilités

Si vous découvrez une vulnérabilité de sécurité, **ne créez pas d'issue publique**. Contactez-nous en privé :

- **Email** : dpo@oenotrac.fr
- **PGP Key** : [À ajouter]

Nous répondrons dans les **48 heures** et travaillerons avec vous pour résoudre le problème avant toute divulgation publique.

---

## 🛡️ Mesures de sécurité implémentées

### Authentification

- **JWT** : Tokens signés avec secret fort
- **Expiration** : Access tokens (24h), Refresh tokens (7 jours)
- **Rotation** : Refresh tokens rotés à chaque utilisation
- **Hashage** : Mots de passe hashés avec bcrypt (cost factor 12)

### API

- **HTTPS** : Obligatoire en production (TLS 1.2+)
- **CORS** : Origines limitées et configurées
- **Rate Limiting** : À implémenter (recommandé)
- **Validation** : Toutes les entrées validées avec Pydantic

### Base de données

- **Connexions sécurisées** : SSL/TLS pour PostgreSQL
- **Principe du moindre privilège** : Utilisateur DB avec permissions limitées
- **Injection SQL** : Prévention via SQLAlchemy ORM (paramètres liés)

### Secrets

- **Variables d'environnement** : Secrets stockés dans `.env` (non commité)
- **Rotation** : Clés API et secrets rotés régulièrement
- **Secrets Managers** : Recommandé pour production (HashiCorp Vault, AWS Secrets Manager)

### Email

- **IMAP/SMTP SSL** : Connexions chiffrées (ports 993/587)
- **App Passwords** : Utilisation de mots de passe d'application (non mots de passe principaux)
- **Validation** : Validation des adresses email

---

## ⚠️ Bonnes pratiques de sécurité

### Pour les développeurs

1. **Ne jamais commiter** :
   - Clés API
   - Mots de passe
   - Secrets
   - Fichiers `.env`

2. **Vérifier les dépendances** :
   ```bash
   # Backend
   pip-audit
   safety check
   
   # Frontend
   npm audit
   ```

3. **Mettre à jour régulièrement** :
   - Dépendances Python/Node
   - Système d'exploitation
   - Base de données

4. **Code Review** : Tous les changements doivent être revus

### Pour les administrateurs

1. **Configuration serveur** :
   - Firewall configuré
   - SSH avec clés (pas de passwords)
   - Mises à jour automatiques

2. **Monitoring** :
   - Logs d'accès
   - Tentatives de connexion échouées
   - Erreurs d'authentification

3. **Sauvegardes** :
   - Sauvegardes régulières de la DB
   - Chiffrement des sauvegardes
   - Tests de restauration

---

## 🔐 Checklist de sécurité

### Déploiement

- [ ] HTTPS configuré (TLS 1.2+)
- [ ] Secrets dans variables d'environnement
- [ ] CORS configuré correctement
- [ ] Firewall configuré
- [ ] Logs sécurisés (pas de secrets dans les logs)
- [ ] Sauvegardes chiffrées
- [ ] Monitoring des erreurs

### Code

- [ ] Pas de secrets hardcodés
- [ ] Validation de toutes les entrées
- [ ] Gestion d'erreurs sans exposition d'informations sensibles
- [ ] Tests de sécurité
- [ ] Dépendances à jour

### Base de données

- [ ] Connexions SSL/TLS
- [ ] Utilisateur avec permissions minimales
- [ ] Sauvegardes régulières
- [ ] Chiffrement au repos (si sensible)

---

## 📋 Audit de sécurité

### Dépendances

Audit régulier des dépendances :

```bash
# Backend
pip-audit --requirement requirements.txt
safety check --file requirements.txt

# Frontend
npm audit
npm audit fix
```

### Code

- **Bandit** (Python) : Détection de problèmes de sécurité
  ```bash
  pip install bandit
  bandit -r backend/app/
  ```

- **ESLint Security Plugin** (TypeScript)
  ```bash
  npm install --save-dev eslint-plugin-security
  ```

### Infrastructure

- **SSL Labs** : Test de configuration SSL/TLS
- **OWASP ZAP** : Scan de vulnérabilités web
- **Nmap** : Scan de ports et services

---

## 🚨 Réponse aux incidents

### En cas de compromission

1. **Isoler** : Désactiver les accès compromis
2. **Analyser** : Identifier l'étendue de la compromission
3. **Corriger** : Appliquer les correctifs
4. **Notifier** : Informer les utilisateurs si nécessaire
5. **Documenter** : Enregistrer l'incident et les mesures prises

### Procédure

1. Créer une issue privée (security)
2. Évaluer la criticité
3. Développer un correctif
4. Tester le correctif
5. Déployer en urgence si critique
6. Publier un advisory si nécessaire

---

## 📚 Ressources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Python Security](https://python.readthedocs.io/en/stable/library/security.html)
- [Node.js Security Best Practices](https://nodejs.org/en/docs/guides/security/)

---

## 🔄 Mises à jour de sécurité

Les mises à jour de sécurité critiques seront publiées dans :
- [CHANGELOG.md](CHANGELOG.md) (section Sécurité)
- [Releases GitHub](../../releases) (avec tag `security`)

---

**Dernière mise à jour** : 2026-01-22  
**Contact sécurité** : dpo@oenotrac.fr
