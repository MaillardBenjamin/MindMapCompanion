# Frontend — MindMapCompanion (React)

Interface web de **MindMapCompanion** (mindmap + tâches + agents IA) construite avec **React 19**, **TypeScript** et **Vite**.

## 🧰 Prérequis

- **Node.js** 18+
- **npm** (ou pnpm/yarn si tu adaptes les commandes)

## 🚀 Démarrage rapide

```bash
cd frontend
npm install
npm run dev
```

Par défaut, l’UI est accessible sur `http://localhost:5173`.

## ⚙️ Configuration

Le frontend consomme l’API FastAPI.

### Variables d’environnement

Crée un fichier `frontend/.env` (ou `frontend/.env.local`) :

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 📦 Scripts

- **`npm run dev`** : serveur de dev Vite
- **`npm run build`** : build de production (TypeScript + Vite)
- **`npm run preview`** : preview du build
- **`npm run lint`** : lint ESLint

## 🧭 Liens utiles

- **README principal** : `../README.md`
- **Documentation** : `../documentation/INDEX.md`
- **Backend** : `../backend/README.md`
