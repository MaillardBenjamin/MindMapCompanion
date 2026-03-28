// Configuration de l'API backend
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8001';

// Endpoints de l'API
export const API_ENDPOINTS = {
  AUTH: {
    REGISTER: '/api/auth/register',
    LOGIN: '/api/auth/login',
    REFRESH: '/api/auth/refresh',
    LOGOUT: '/api/auth/logout',
  },
  USERS: {
    ME: '/api/users/me',
  },
  MINDMAPS: {
    LIST: '/api/mindmaps',
    CREATE: '/api/mindmaps',
    GET: (id: number) => `/api/mindmaps/${id}`,
    UPDATE: (id: number) => `/api/mindmaps/${id}`,
    DELETE: (id: number) => `/api/mindmaps/${id}`,
  },
  NODES: {
    CREATE: '/api/nodes',
    GET_BY_MINDMAP: (mindmapId: number) => `/api/nodes/mindmap/${mindmapId}`,
    GET: (id: number) => `/api/nodes/${id}`,
    UPDATE: (id: number) => `/api/nodes/${id}`,
    DELETE: (id: number) => `/api/nodes/${id}`,
  },
  TRIGGERS: {
    CREATE: '/api/triggers',
    GET_BY_NODE: (nodeId: number) => `/api/triggers/node/${nodeId}`,
    GET: (id: number) => `/api/triggers/${id}`,
    UPDATE: (id: number) => `/api/triggers/${id}`,
    DELETE: (id: number) => `/api/triggers/${id}`,
    EXECUTE: (id: string) => `/api/triggers/${id}/execute`,
    EXECUTE_STREAM: (id: string) => `/api/triggers/${id}/execute/stream`,
  },
  CONFIGURABLE_AGENTS: {
    LIST: '/api/configurable-agents',
    GET: (id: number) => `/api/configurable-agents/${id}`,
    GET_BY_SLUG: (slug: string) => `/api/configurable-agents/slug/${slug}`,
    CREATE: '/api/configurable-agents',
    UPDATE: (id: number) => `/api/configurable-agents/${id}`,
    DELETE: (id: number) => `/api/configurable-agents/${id}`,
    EXECUTE: (id: number) => `/api/configurable-agents/${id}/execute`,
    EXECUTE_BY_SLUG: (slug: string) => `/api/configurable-agents/slug/${slug}/execute`,
  },
  ACTIONS: {
    CREATE: '/api/actions',
    GET_BY_TRIGGER: (triggerId: number) => `/api/actions/trigger/${triggerId}`,
    GET: (id: number) => `/api/actions/${id}`,
    UPDATE: (id: number) => `/api/actions/${id}`,
    DELETE: (id: number) => `/api/actions/${id}`,
  },
  AGENTS: {
    LIST: '/api/agents',
    MINDMAP_ORGANIZE: '/api/agents/mindmap/organize',
    MINDMAP_REORGANIZE: '/api/agents/mindmap/reorganize',
  },
  HISTORY: {
    LIST: '/api/history',
  },
  SETTINGS: {
    GET: '/api/settings',
    UPDATE: '/api/settings',
    TEST: (service: string) => `/api/settings/test/${service}`,
  },
} as const;
