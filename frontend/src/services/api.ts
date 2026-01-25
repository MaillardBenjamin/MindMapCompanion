import { API_BASE_URL, API_ENDPOINTS } from '../config/api';

// Types pour les réponses API
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface ApiError {
  detail: string;
}

// Classe pour gérer les erreurs API
export class ApiErrorResponse extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = 'ApiErrorResponse';
  }
}

// Fonction utilitaire pour construire l'URL complète
const buildUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`;
};

// Fonction pour obtenir le token d'accès depuis le localStorage
const getAccessToken = (): string | null => {
  return localStorage.getItem('access_token');
};

// Fonction pour obtenir le refresh token depuis le localStorage
export const getRefreshToken = (): string | null => {
  return localStorage.getItem('refresh_token');
};

// Fonction pour stocker les tokens
export const setTokens = (accessToken: string, refreshToken: string): void => {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
};

// Fonction pour supprimer les tokens
export const removeTokens = (): void => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

// Fonction pour gérer les requêtes fetch avec authentification
const fetchWithAuth = async (
  url: string,
  options: RequestInit = {}
): Promise<Response> => {
  const accessToken = getAccessToken();
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Si le token a expiré, essayer de le rafraîchir
  if (response.status === 401 && accessToken) {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        const newTokens = await refreshAccessToken(refreshToken);
        setTokens(newTokens.access_token, newTokens.refresh_token);
        
        // Réessayer la requête avec le nouveau token
        headers['Authorization'] = `Bearer ${newTokens.access_token}`;
        return fetch(url, {
          ...options,
          headers,
        });
      } catch (error) {
        // Le refresh token est invalide, déconnexion
        removeTokens();
        throw error;
      }
    }
  }

  return response;
};

// Fonction pour gérer les erreurs de réponse
const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    let errorDetail = 'Une erreur est survenue';
    try {
      const errorData: ApiError = await response.json();
      errorDetail = errorData.detail || errorDetail;
    } catch {
      errorDetail = `Erreur ${response.status}: ${response.statusText}`;
    }
    throw new ApiErrorResponse(response.status, errorDetail);
  }

  return response.json();
};

// Service API pour l'authentification
export const authApi = {
  // Inscription
  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    const response = await fetch(buildUrl(API_ENDPOINTS.AUTH.REGISTER), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    return handleResponse<TokenResponse>(response);
  },

  // Connexion
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await fetch(buildUrl(API_ENDPOINTS.AUTH.LOGIN), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    return handleResponse<TokenResponse>(response);
  },

  // Rafraîchir le token
  refreshToken: async (refreshToken: string): Promise<TokenResponse> => {
    const response = await fetch(buildUrl(API_ENDPOINTS.AUTH.REFRESH), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    return handleResponse<TokenResponse>(response);
  },

  // Déconnexion
  logout: async (refreshToken: string): Promise<void> => {
    const response = await fetch(buildUrl(API_ENDPOINTS.AUTH.LOGOUT), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      // Même si l'API renvoie une erreur, on supprime les tokens localement
      console.warn('Erreur lors de la déconnexion côté serveur');
    }
  },
};

// Fonction helper pour rafraîchir le token
export const refreshAccessToken = async (refreshToken: string): Promise<TokenResponse> => {
  return authApi.refreshToken(refreshToken);
};

// Service API pour les utilisateurs
export const usersApi = {
  // Récupérer les informations de l'utilisateur connecté
  getMe: async (): Promise<UserResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.USERS.ME), {
      method: 'GET',
    });

    return handleResponse<UserResponse>(response);
  },
};

// Types pour les mindmaps
export interface MindmapResponse {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MindmapCreate {
  name: string;
  description?: string | null;
}

export interface MindmapUpdate {
  name?: string;
  description?: string | null;
  is_active?: boolean;
}

export interface NodeResponse {
  id: number;
  mindmap_id: number;
  parent_id: number | null;
  label: string;
  description: string | null;
  color: string;
  position_x: number;
  position_y: number;
  status: string;
  is_root: boolean;
  created_at: string;
  updated_at: string;
}

export interface NodeCreate {
  mindmap_id: number;
  parent_id?: number | null;
  label: string;
  description?: string | null;
  color?: string;
  position_x: number;
  position_y: number;
  is_root?: boolean;
  status?: string;
}

export interface NodeUpdate {
  label?: string;
  description?: string | null;
  color?: string;
  position_x?: number;
  position_y?: number;
  parent_id?: number | null;
  status?: string;
}

export interface TriggerResponse {
  id: number;
  node_id: number;
  trigger_type: string;  // email_received, date_reached, cron, state_changed, manual
  enabled: boolean;
  config: Record<string, unknown> | null;
  last_fired_at?: string | null;
  dedupe_key?: string | null;
}

export interface TriggerCreate {
  node_id: number;
  trigger_type: string;  // email_received, date_reached, cron, state_changed, manual
  enabled?: boolean;
  config?: Record<string, unknown> | null;
}

export interface TriggerUpdate {
  trigger_type?: string;
  enabled?: boolean;
  config?: Record<string, unknown> | null;
}

export interface ActionResponse {
  id: number;
  trigger_id: number;
  name: string;
  type: string;
  order: number;
  enabled: boolean;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ActionCreate {
  trigger_id: number;
  name: string;
  type: string;
  order?: number;
  enabled?: boolean;
  config?: Record<string, unknown> | null;
}

export interface ActionUpdate {
  name?: string;
  type?: string;
  order?: number;
  enabled?: boolean;
  config?: Record<string, unknown> | null;
}

// Service API pour les mindmaps
export const mindmapsApi = {
  // Créer un mindmap
  create: async (data: MindmapCreate): Promise<MindmapResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.MINDMAPS.CREATE), {
      method: 'POST',
      body: JSON.stringify(data),
    });

    return handleResponse<MindmapResponse>(response);
  },

  // Lister tous les mindmaps de l'utilisateur
  list: async (): Promise<MindmapResponse[]> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.MINDMAPS.LIST), {
      method: 'GET',
    });

    return handleResponse<MindmapResponse[]>(response);
  },

  // Récupérer un mindmap avec ses nœuds
  get: async (id: number): Promise<MindmapResponse & { nodes: NodeResponse[] }> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.MINDMAPS.GET(id)), {
      method: 'GET',
    });

    return handleResponse<MindmapResponse & { nodes: NodeResponse[] }>(response);
  },

  // Mettre à jour un mindmap
  update: async (id: number, data: MindmapUpdate): Promise<MindmapResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.MINDMAPS.UPDATE(id)), {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    return handleResponse<MindmapResponse>(response);
  },

  // Supprimer un mindmap
  delete: async (id: number): Promise<void> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.MINDMAPS.DELETE(id)), {
      method: 'DELETE',
    });

    if (!response.ok) {
      await handleResponse<{ detail: string }>(response);
    }
  },
};

// Service API pour les nodes
export const nodesApi = {
  // Créer un nœud
  create: async (data: NodeCreate): Promise<NodeResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.NODES.CREATE), {
      method: 'POST',
      body: JSON.stringify(data),
    });

    return handleResponse<NodeResponse>(response);
  },

  // Lister les nœuds d'un mindmap
  listByMindmap: async (mindmapId: number): Promise<NodeResponse[]> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.NODES.GET_BY_MINDMAP(mindmapId)), {
      method: 'GET',
    });

    return handleResponse<NodeResponse[]>(response);
  },

  // Récupérer un nœud
  get: async (id: number): Promise<NodeResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.NODES.GET(id)), {
      method: 'GET',
    });

    return handleResponse<NodeResponse>(response);
  },

  // Mettre à jour un nœud
  update: async (id: number, data: NodeUpdate): Promise<NodeResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.NODES.UPDATE(id)), {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    return handleResponse<NodeResponse>(response);
  },

  // Supprimer un nœud
  delete: async (id: number): Promise<void> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.NODES.DELETE(id)), {
      method: 'DELETE',
    });

    if (!response.ok) {
      await handleResponse<{ detail: string }>(response);
    }
  },
};

// Service API pour les triggers
export const triggersApi = {
  // Créer un trigger
  create: async (data: TriggerCreate): Promise<TriggerResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.TRIGGERS.CREATE), {
      method: 'POST',
      body: JSON.stringify(data),
    });

    return handleResponse<TriggerResponse>(response);
  },

  // Lister les triggers d'un nœud
  listByNode: async (nodeId: number): Promise<TriggerResponse[]> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.TRIGGERS.GET_BY_NODE(nodeId)), {
      method: 'GET',
    });

    return handleResponse<TriggerResponse[]>(response);
  },

  // Récupérer un trigger
  get: async (id: number): Promise<TriggerResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.TRIGGERS.GET(id)), {
      method: 'GET',
    });

    return handleResponse<TriggerResponse>(response);
  },

  // Mettre à jour un trigger
  update: async (id: number, data: TriggerUpdate): Promise<TriggerResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.TRIGGERS.UPDATE(id)), {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    return handleResponse<TriggerResponse>(response);
  },

  // Supprimer un trigger
  delete: async (id: number): Promise<void> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.TRIGGERS.DELETE(id)), {
      method: 'DELETE',
    });

    if (!response.ok) {
      await handleResponse<{ detail: string }>(response);
    }
  },

  // Lancer un trigger manuellement
  execute: async (triggerId: string, data: TriggerManualExecuteRequest): Promise<TriggerManualExecuteResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.TRIGGERS.EXECUTE(triggerId)), {
      method: 'POST',
      body: JSON.stringify(data),
    });

    return handleResponse<TriggerManualExecuteResponse>(response);
  },
};

// Service API pour les actions
export const actionsApi = {
  // Créer une action
  create: async (data: ActionCreate): Promise<ActionResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.ACTIONS.CREATE), {
      method: 'POST',
      body: JSON.stringify(data),
    });

    return handleResponse<ActionResponse>(response);
  },

  // Lister les actions d'un trigger
  listByTrigger: async (triggerId: number): Promise<ActionResponse[]> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.ACTIONS.GET_BY_TRIGGER(triggerId)), {
      method: 'GET',
    });

    return handleResponse<ActionResponse[]>(response);
  },

  // Récupérer une action
  get: async (id: number): Promise<ActionResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.ACTIONS.GET(id)), {
      method: 'GET',
    });

    return handleResponse<ActionResponse>(response);
  },

  // Mettre à jour une action
  update: async (id: number, data: ActionUpdate): Promise<ActionResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.ACTIONS.UPDATE(id)), {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    return handleResponse<ActionResponse>(response);
  },

  // Supprimer une action
  delete: async (id: number): Promise<void> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.ACTIONS.DELETE(id)), {
      method: 'DELETE',
    });

    if (!response.ok) {
      await handleResponse<{ detail: string }>(response);
    }
  },
};

// Types pour les agents IA
export interface AgentInfo {
  name: string;
  description: string;
  endpoint: string;
  method: string;
}

export interface OrganizeRequest {
  mindmap_id: number;
  text: string;
  auto_apply?: boolean;
}

export interface ReorganizeRequest {
  mindmap_id: number;
  auto_apply?: boolean;
  focus_area?: string;
}

export interface NodeSuggestion {
  action: 'create' | 'update';
  node_id: number | null;
  parent_id: number | null;
  label: string;
  description: string;
  reasoning: string;
}

export interface OrganizeResponse {
  success: boolean;
  message: string;
  data: {
    suggestions: NodeSuggestion[];
    created_nodes: { id: number; label: string; parent_id: number | null }[];
    updated_nodes: { id: number; label: string }[];
    auto_applied: boolean;
  };
}

export interface ReorganizeAction {
  action: 'move' | 'rename' | 'merge' | 'delete';
  node_id: number;
  new_parent_id?: number;
  new_label?: string;
  merge_into_id?: number;
  reasoning: string;
}

export interface ReorganizeResponse {
  success: boolean;
  message: string;
  data: {
    proposed_actions: ReorganizeAction[];
    applied_actions: { action: string; node_id: number; [key: string]: unknown }[];
    skipped_actions: { action: string; node_id: number; reason: string }[];
    improvements: string[];
    auto_applied: boolean;
  };
}

// Service API pour les agents IA
export const agentsApi = {
  // Lister les agents disponibles
  list: async (): Promise<AgentInfo[]> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.AGENTS.LIST), {
      method: 'GET',
    });

    return handleResponse<AgentInfo[]>(response);
  },

  // Organiser du texte dans le mindmap
  organizeText: async (data: OrganizeRequest): Promise<OrganizeResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.AGENTS.MINDMAP_ORGANIZE), {
      method: 'POST',
      body: JSON.stringify(data),
    });

    return handleResponse<OrganizeResponse>(response);
  },

  // Réorganiser le mindmap
  reorganizeMindmap: async (data: ReorganizeRequest): Promise<ReorganizeResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.AGENTS.MINDMAP_REORGANIZE), {
      method: 'POST',
      body: JSON.stringify(data),
    });

    return handleResponse<ReorganizeResponse>(response);
  },
};

// Types pour les agents configurables
export interface ConfigurableAgentResponse {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  prompt_template: string;
  input_schema: Record<string, any> | null;
  output_schema: any | null;
  tools: string[] | null;
  mcp_servers: string[] | null;
  persona: string | null;
  instructions: string | null;
  is_active: boolean;
  is_public: boolean;
  user_id: number;
  created_at: string;
  updated_at: string;
}

export interface ConfigurableAgentListResponse {
  agents: ConfigurableAgentResponse[];
}

export interface TriggerManualExecuteRequest {
  trigger_id?: string;
  task_type: 'agent' | 'action';
  task_id: string;
  output_type: 'screen' | 'email';
  input_text?: string;
  email_config?: {
    to: string;
    subject?: string;
  };
}

export interface TriggerManualExecuteResponse {
  success: boolean;
  message: string;
  execution_id?: string;
  output?: any;
  email_sent?: boolean;
}

// Service API pour les agents configurables
export const configurableAgentsApi = {
  // Lister les agents configurables
  list: async (skip = 0, limit = 100, includePublic = true): Promise<ConfigurableAgentListResponse> => {
    const response = await fetchWithAuth(
      buildUrl(`${API_ENDPOINTS.CONFIGURABLE_AGENTS.LIST}?skip=${skip}&limit=${limit}&include_public=${includePublic}`),
      {
        method: 'GET',
      }
    );

    return handleResponse<ConfigurableAgentListResponse>(response);
  },

  // Récupérer un agent par ID
  get: async (id: number): Promise<ConfigurableAgentResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.CONFIGURABLE_AGENTS.GET(id)), {
      method: 'GET',
    });

    return handleResponse<ConfigurableAgentResponse>(response);
  },

  // Exécuter un agent
  execute: async (id: number, inputText: string, options?: any): Promise<any> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.CONFIGURABLE_AGENTS.EXECUTE(id)), {
      method: 'POST',
      body: JSON.stringify({
        input_text: inputText,
        options,
      }),
    });

    return handleResponse<any>(response);
  },
};

// Service API pour l'exécution manuelle de trigger
export const triggerExecutionApi = {
  // Lancer un trigger manuellement
  execute: async (triggerId: string, data: TriggerManualExecuteRequest): Promise<TriggerManualExecuteResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.TRIGGERS.EXECUTE(triggerId)), {
      method: 'POST',
      body: JSON.stringify(data),
    });

    return handleResponse<TriggerManualExecuteResponse>(response);
  },
};

// Types pour l'historique
export interface HistoryItem {
  id: string;
  type: 'agent_execution' | 'trigger_execution' | 'action_execution' | 'node_created' | 'node_updated' | 'trigger_created' | 'trigger_updated' | 'trigger_deleted' | 'action_created' | 'action_updated' | 'action_deleted' | 'event';
  created_at: string;
  title: string;
  description?: string | null;
  status?: string | null;
  node_id?: string | number | null;
  node_label?: string | null;
  trigger_id?: string | number | null;
  action_id?: string | number | null;
  agent_id?: number | null;
  agent_name?: string | null;
  metadata?: Record<string, any>;
}

export interface HistoryListResponse {
  items: HistoryItem[];
  total: number;
}

// Service API pour l'historique
export const historyApi = {
  // Récupérer l'historique
  list: async (skip: number = 0, limit: number = 50, nodeId?: number): Promise<HistoryListResponse> => {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (nodeId) {
      params.append('node_id', nodeId.toString());
    }
    
    const response = await fetchWithAuth(`${buildUrl(API_ENDPOINTS.HISTORY.LIST)}?${params.toString()}`, {
      method: 'GET',
    });

    return handleResponse<HistoryListResponse>(response);
  },
};

// Types pour les paramètres
export interface SettingsResponse {
  imap_host: string;
  imap_port: number;
  imap_user: string;
  imap_password: string;
  imap_folder: string;
  imap_ssl: boolean;
  imap_poll_minutes: number;
  agno_model: string;
  agno_api_key: string;
  openai_api_key: string;
  mistral_api_key: string;
  google_search_api_key: string;
  google_search_engine_id: string;
  bing_search_api_key: string;
  search_provider: string;
}

export interface SettingsUpdate {
  imap_host?: string;
  imap_port?: number;
  imap_user?: string;
  imap_password?: string;
  imap_folder?: string;
  imap_ssl?: boolean;
  imap_poll_minutes?: number;
  agno_model?: string;
  agno_api_key?: string;
  openai_api_key?: string;
  mistral_api_key?: string;
  google_search_api_key?: string;
  google_search_engine_id?: string;
  bing_search_api_key?: string;
  search_provider?: string;
}

export interface TestConnectionResponse {
  status: 'success' | 'error';
  message: string;
}

// Service API pour les paramètres
export const settingsApi = {
  // Récupérer les paramètres
  get: async (): Promise<SettingsResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.SETTINGS.GET), {
      method: 'GET',
    });
    return handleResponse<SettingsResponse>(response);
  },

  // Mettre à jour les paramètres
  update: async (settings: SettingsUpdate): Promise<{ message: string; note?: string }> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.SETTINGS.UPDATE), {
      method: 'POST',
      body: JSON.stringify(settings),
    });
    return handleResponse<{ message: string; note?: string }>(response);
  },

  // Tester une connexion
  test: async (service: string): Promise<TestConnectionResponse> => {
    const response = await fetchWithAuth(buildUrl(API_ENDPOINTS.SETTINGS.TEST(service)), {
      method: 'POST',
    });
    return handleResponse<TestConnectionResponse>(response);
  },
};
