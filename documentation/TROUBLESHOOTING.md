# Guide de Dépannage

Ce guide aide à résoudre les problèmes courants rencontrés avec Personal Assistant.

## 📋 Table des matières

- [Problèmes Backend](#problèmes-backend)
- [Problèmes Frontend](#problèmes-frontend)
- [Problèmes Base de données](#problèmes-base-de-données)
- [Problèmes Email](#problèmes-email)
- [Problèmes Agents IA](#problèmes-agents-ia)
- [Problèmes Triggers](#problèmes-triggers)
- [Problèmes Performance](#problèmes-performance)

---

## 🔧 Problèmes Backend

### L'API ne démarre pas

**Symptômes** :
- Erreur au démarrage de uvicorn
- Port 8000 déjà utilisé

**Solutions** :

```bash
# Vérifier si le port est utilisé
sudo lsof -i :8000

# Tuer le processus si nécessaire
sudo kill -9 <PID>

# Vérifier les logs
tail -f backend/logs/app.log

# Vérifier les variables d'environnement
cat backend/.env
```

### Erreur de connexion à la base de données

**Symptômes** :
- `sqlalchemy.exc.OperationalError: could not connect to server`
- `asyncpg.exceptions.InvalidPasswordError`

**Solutions** :

```bash
# Vérifier que PostgreSQL est démarré
sudo systemctl status postgresql

# Vérifier la connexion
psql -U personal_assistant -h localhost -d personal_assistant

# Vérifier DATABASE_URL dans .env
echo $DATABASE_URL
```

### Erreur CORS

**Symptômes** :
- `Access to fetch at '...' from origin '...' has been blocked by CORS policy`

**Solutions** :

```python
# Vérifier CORS_ORIGINS dans .env
CORS_ORIGINS=http://localhost:5173,https://example.com

# Redémarrer le backend après modification
sudo systemctl restart personal-assistant
```

### Erreur JWT

**Symptômes** :
- `401 Unauthorized`
- `Invalid token`

**Solutions** :

```bash
# Vérifier JWT_SECRET_KEY dans .env
# Doit être une chaîne forte et unique

# Vérifier l'expiration
# JWT_EXP_MINUTES=1440 (24h par défaut)

# Vérifier les logs
grep "JWT" backend/logs/app.log
```

---

## 🎨 Problèmes Frontend

### Le frontend ne se compile pas

**Symptômes** :
- Erreurs TypeScript
- Erreurs de dépendances

**Solutions** :

```bash
# Nettoyer et réinstaller
rm -rf node_modules package-lock.json
npm install

# Vérifier les erreurs TypeScript
npm run type-check

# Vérifier ESLint
npm run lint
```

### L'API n'est pas accessible depuis le frontend

**Symptômes** :
- `Failed to fetch`
- `Network error`

**Solutions** :

```bash
# Vérifier VITE_API_BASE_URL
cat frontend/.env
# Doit être : VITE_API_BASE_URL=http://localhost:8000

# Vérifier que le backend est démarré
curl http://localhost:8000/health

# Vérifier CORS côté backend
```

### Erreurs de routing

**Symptômes** :
- 404 sur les routes React
- Page blanche après refresh

**Solutions** :

```nginx
# Configuration Nginx correcte
location / {
    try_files $uri $uri/ /index.html;
}
```

---

## 🗄️ Problèmes Base de données

### Migrations échouent

**Symptômes** :
- `alembic.util.exc.CommandError`
- Colonnes manquantes

**Solutions** :

```bash
# Vérifier l'état actuel
alembic current

# Voir l'historique
alembic history

# Rollback si nécessaire
alembic downgrade -1

# Réappliquer
alembic upgrade head
```

### Erreur de connexion asyncpg

**Symptômes** :
- `asyncpg.exceptions.InvalidPasswordError`
- `asyncpg.exceptions.ConnectionDoesNotExistError`

**Solutions** :

```bash
# Vérifier le format de DATABASE_URL
# Doit être : postgresql+asyncpg://user:pass@host:port/db

# Tester la connexion
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://user:pass@localhost:5432/db'))"
```

### Performance lente

**Symptômes** :
- Requêtes lentes
- Timeouts

**Solutions** :

```sql
-- Vérifier les index
SELECT * FROM pg_indexes WHERE tablename = 'nodes';

-- Analyser les requêtes lentes
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;

-- VACUUM et ANALYZE
VACUUM ANALYZE;
```

---

## 📧 Problèmes Email

### Emails non reçus

**Symptômes** :
- Pas de nœuds créés depuis les emails
- Erreurs IMAP dans les logs

**Solutions** :

```bash
# Vérifier la connexion IMAP
python -c "
import imaplib
import ssl
context = ssl.create_default_context()
conn = imaplib.IMAP4_SSL('mail.example.com', 993, ssl_context=context)
conn.login('user@example.com', 'password')
conn.select('INBOX')
print('Connexion OK')
"

# Vérifier les logs
grep "IMAP" backend/logs/app.log

# Vérifier les variables d'environnement
echo $IMAP_HOST
echo $IMAP_PORT
echo $IMAP_USER
```

### Erreur SSL IMAP

**Symptômes** :
- `ssl.SSLError: [SSL: WRONG_VERSION_NUMBER]`

**Solutions** :

```python
# Vérifier le port (993 pour SSL, 143 pour non-SSL)
IMAP_PORT=993  # SSL
IMAP_SSL=true

# Vérifier la configuration du serveur email
# Gandi : Port 993 avec SSL
```

### Emails non envoyés

**Symptômes** :
- Erreurs SMTP
- Emails dans la queue mais non envoyés

**Solutions** :

```bash
# Vérifier la connexion SMTP
python -c "
import smtplib
from email.mime.text import MIMEText
msg = MIMEText('Test')
msg['Subject'] = 'Test'
msg['From'] = 'from@example.com'
msg['To'] = 'to@example.com'
s = smtplib.SMTP('smtp.example.com', 587)
s.starttls()
s.login('user@example.com', 'password')
s.send_message(msg)
s.quit()
print('Email envoyé')
"

# Vérifier les logs
grep "SMTP" backend/logs/app.log
```

---

## 🤖 Problèmes Agents IA

### Agent ne s'exécute pas

**Symptômes** :
- Timeout
- Erreur OpenAI API

**Solutions** :

```bash
# Vérifier la clé API
echo $OPENAI_API_KEY
echo $AGNO_API_KEY

# Tester la connexion OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Vérifier les logs
grep "ConfigurableAgent" backend/logs/app.log
```

### Sortie non parsée

**Symptômes** :
- `output_parsed` est null
- Erreur de parsing JSON

**Solutions** :

```python
# Vérifier le schéma de sortie dans la config de l'agent
# Le schéma doit être valide JSON

# Vérifier les logs de parsing
grep "parse" backend/logs/app.log

# L'agent doit retourner du Markdown, pas du JSON brut
```

### Outils non disponibles

**Symptômes** :
- `DuckDuckGoTools d'Agno non disponible`
- Recherche web ne fonctionne pas

**Solutions** :

```bash
# Installer ddgs
pip install ddgs

# Vérifier l'import
python -c "from agno.tools.duckduckgo import DuckDuckGoTools; print('OK')"
```

---

## ⚡ Problèmes Triggers

### Trigger cron ne s'exécute pas

**Symptômes** :
- Pas d'exécution à l'heure prévue
- `last_fired_at` reste null

**Solutions** :

```bash
# Vérifier que le scheduler est démarré
grep "Scheduler démarré" backend/logs/app.log

# Vérifier l'expression cron
# Format : "minute heure * * jours"
# Exemple : "0 9 * * 1,3,5" (lundi, mercredi, vendredi à 9h)

# Vérifier que le trigger est activé
# enabled = true dans la DB

# Vérifier les logs du scheduler
grep "Scheduler" backend/logs/app.log
```

### Trigger exécuté plusieurs fois

**Symptômes** :
- Doublons d'exécution
- `dedupe_key` non fonctionnel

**Solutions** :

```python
# Vérifier que dedupe_key est défini
# Le scheduler doit mettre à jour last_fired_at

# Vérifier l'idempotence dans execute_trigger_with_config
```

### Erreur lors de l'exécution manuelle

**Symptômes** :
- 500 Internal Server Error
- Erreur dans les logs

**Solutions** :

```bash
# Vérifier les logs détaillés
tail -f backend/logs/app.log

# Vérifier la configuration du trigger
# task_type, task_id, output_type doivent être définis

# Tester l'agent/action séparément
```

---

## 🚀 Problèmes Performance

### API lente

**Symptômes** :
- Temps de réponse > 1s
- Timeouts

**Solutions** :

```bash
# Vérifier les requêtes lentes dans les logs
grep "execution_time" backend/logs/app.log

# Optimiser les requêtes DB
# Ajouter des index si nécessaire

# Augmenter le nombre de workers
uvicorn app.main:app --workers 4
```

### Frontend lent

**Symptômes** :
- Temps de chargement > 3s
- Rendu lent

**Solutions** :

```bash
# Vérifier la taille du bundle
npm run build
ls -lh frontend/dist/

# Optimiser les images
# Utiliser le lazy loading
# Code splitting
```

### Base de données lente

**Symptômes** :
- Requêtes > 100ms
- Locks fréquents

**Solutions** :

```sql
-- Analyser les requêtes lentes
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;

-- Vérifier les index manquants
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE tablename IN ('nodes', 'triggers', 'actions');

-- VACUUM régulier
VACUUM ANALYZE;
```

---

## 🔍 Commandes utiles

### Logs

```bash
# Backend
tail -f backend/logs/app.log
sudo journalctl -u personal-assistant -f

# Frontend (dans la console du navigateur)
# DevTools > Console
```

### Vérifications

```bash
# Santé de l'API
curl http://localhost:8000/health

# Connexion DB
psql -U personal_assistant -h localhost -d personal_assistant

# Variables d'environnement
env | grep -E "(DATABASE|JWT|IMAP|SMTP|OPENAI)"
```

### Debug

```bash
# Mode debug Python
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug

# Mode debug Frontend
npm run dev
# DevTools > Sources > Breakpoints
```

---

## 📞 Support

Si le problème persiste :

1. Consultez les [Issues GitHub](../../issues)
2. Vérifiez la [documentation](INDEX.md)
3. Ouvrez une nouvelle issue avec :
   - Description détaillée
   - Logs pertinents
   - Étapes pour reproduire
   - Environnement (OS, versions)

---

**Note** : Ce guide est mis à jour régulièrement. Contribuez avec vos solutions !
