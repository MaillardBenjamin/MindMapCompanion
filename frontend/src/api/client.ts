import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  // Utiliser access_token ou jwt qui est stocké par le système d'authentification
  const token = localStorage.getItem("access_token") || localStorage.getItem("jwt");
  console.log('[API Client] Requête:', config.method?.toUpperCase(), config.url);
  console.log('[API Client] Token présent:', !!token);
  console.log('[API Client] Token (premiers 20 chars):', token ? token.substring(0, 20) + '...' : 'null');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    console.log('[API Client] Header Authorization ajouté');
  } else {
    console.warn('[API Client] ⚠️ Aucun token trouvé dans localStorage');
  }
  return config;
});

export async function login(username: string, password: string) {
  const params = new URLSearchParams();
  params.append("username", username);
  params.append("password", password);
  const { data } = await api.post("/auth/token", params);
  // Stocker le token dans les deux clés pour compatibilité
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("jwt", data.access_token);
  return data;
}

export async function getMindmap() {
  const { data } = await api.get("/mindmap");
  return data;
}

export async function ingestText(text: string, source = "ui") {
  const { data } = await api.post("/ingest/text", { text, source });
  return data;
}

export async function getNode(id: string) {
  const { data } = await api.get(`/nodes/${id}`);
  return data;
}

export async function updateNode(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch(`/nodes/${id}`, payload);
  return data;
}

export async function listProposals(status?: string, nodeId?: string) {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  if (nodeId) params.node_id = nodeId;
  const { data } = await api.get("/proposals", { params });
  return data;
}

export async function approveProposal(id: string) {
  const { data } = await api.post(`/proposals/${id}/approve_and_apply`);
  return data;
}

export async function rejectProposal(id: string) {
  const { data } = await api.post(`/proposals/${id}/reject`);
  return data;
}

export async function listTriggers(nodeId: string) {
  const { data } = await api.get("/api/triggers/node/" + nodeId);
  return data;
}

export async function createTrigger(payload: {
  node_id: string;
  trigger_type: string;
  config?: Record<string, any>;
  enabled?: boolean;
}) {
  const { data } = await api.post("/api/triggers", payload);
  return data;
}

export async function updateTrigger(
  triggerId: string,
  payload: {
    trigger_type?: string;
    config?: Record<string, any>;
    enabled?: boolean;
  }
) {
  const { data } = await api.put(`/api/triggers/${triggerId}`, payload);
  return data;
}

export async function deleteTrigger(triggerId: string) {
  const { data } = await api.delete(`/api/triggers/${triggerId}`);
  return data;
}

export async function executeTrigger(triggerId: string, payload: {
  task_type: string;
  task_id: string;
  output_type?: string;
  input_text?: string;
}) {
  const { data } = await api.post(`/api/triggers/${triggerId}/execute`, payload);
  return data;
}

export async function listActions(nodeId: string | number) {
  // Convertir en nombre pour l'API backend
  const numericNodeId = typeof nodeId === 'string' ? parseInt(nodeId, 10) : nodeId;
  const { data } = await api.get("/actions", { params: { node_id: numericNodeId } });
  return data;
}

export async function createAction(payload: {
  node_id: string | number;
  action_type: string;
  mode?: string;
  config?: Record<string, any>;
  enabled?: boolean;
}) {
  // Convertir node_id en nombre pour l'API backend
  const numericPayload = {
    ...payload,
    node_id: typeof payload.node_id === 'string' ? parseInt(payload.node_id, 10) : payload.node_id,
  };
  console.log('[API Client] createAction appelé avec payload:', numericPayload);
  try {
    const { data } = await api.post("/actions", numericPayload);
    console.log('[API Client] createAction succès:', data);
    return data;
  } catch (error: any) {
    console.error('[API Client] createAction erreur:', error);
    console.error('[API Client] Status:', error.response?.status);
    console.error('[API Client] Response data:', error.response?.data);
    throw error;
  }
}

// Configurable Agents API
export async function listConfigurableAgents() {
  const { data } = await api.get("/api/configurable-agents");
  return data;
}

export async function getConfigurableAgent(agentId: number) {
  const { data } = await api.get(`/api/configurable-agents/${agentId}`);
  return data;
}

export async function getConfigurableAgentBySlug(slug: string) {
  const { data } = await api.get(`/api/configurable-agents/slug/${slug}`);
  return data;
}

export async function createConfigurableAgent(payload: {
  name: string;
  slug: string;
  description?: string;
  markdown_config?: string;
  prompt_template?: string;
  output_schema?: any;
  tools?: string[];
  mcp_servers?: string[];
  persona?: string;
  instructions?: string;
  is_active?: boolean;
  is_public?: boolean;
}) {
  const { data } = await api.post("/api/configurable-agents", payload);
  return data;
}

export async function executeConfigurableAgent(agentId: number, inputText: string, options?: Record<string, any>) {
  const { data } = await api.post(`/api/configurable-agents/${agentId}/execute`, {
    input_text: inputText,
    options: options || {},
  });
  return data;
}

export async function loadAgentsFromFiles() {
  const { data } = await api.post("/admin/load-agents-from-files");
  return data;
}
