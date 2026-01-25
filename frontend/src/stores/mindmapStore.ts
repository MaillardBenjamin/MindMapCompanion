import { create } from 'zustand';
import type { Node, Edge } from '@xyflow/react';
import { 
  mindmapsApi, 
  nodesApi, 
  triggersApi, 
  actionsApi,
  agentsApi,
  type MindmapResponse,
  type NodeResponse,
  type NodeCreate,
  type TriggerResponse,
  type TriggerCreate,
  type ActionResponse,
  type ActionCreate,
  ApiErrorResponse,
} from '../services/api';
import { calculateBidirectionalLayout, findOptimalHandles } from '../utils/elkLayout';
import type { NodeStatus } from '../../../shared/types';
import { isValidStatus } from '../utils/nodeStatus';

export interface MindmapNodeData {
  label: string;
  description?: string;
  color?: string;
  triggers?: TriggerResponse[];
  isRoot?: boolean;
  status?: NodeStatus;
  // IDs backend
  backendId?: number;
  backendParentId?: number | null;
}

export interface Trigger {
  id: string | number;
  type: 'schedule' | 'webhook' | 'condition' | 'manual';
  name: string;
  config?: Record<string, unknown>;
  enabled: boolean;
  backendId?: number;
}

interface MindmapState {
  // Mindmaps
  mindmaps: MindmapResponse[];
  currentMindmap: MindmapResponse | null;
  isLoadingMindmaps: boolean;
  
  // Nodes et edges
  nodes: Node<MindmapNodeData>[];
  edges: Edge[];
  selectedNode: Node<MindmapNodeData> | null;
  
  // État de traitement
  isProcessing: boolean;
  isSaving: boolean;
  isReorganizing: boolean;
  isUpdatingNode: boolean;
  error: string | null;

  // Actions pour les mindmaps
  loadMindmaps: () => Promise<void>;
  createMindmap: (name: string, description?: string) => Promise<MindmapResponse | null>;
  selectMindmap: (mindmapId: number) => Promise<void>;
  deleteMindmap: (mindmapId: number) => Promise<void>;
  updateMindmap: (mindmapId: number, name?: string, description?: string) => Promise<void>;

  // Actions pour les nodes
  loadNodes: (mindmapId: number) => Promise<void>;
  setNodes: (nodes: Node<MindmapNodeData>[]) => void;
  setEdges: (edges: Edge[]) => void;
  updateEdgesHandles: () => void;
  addNode: (node: Node<MindmapNodeData>, skipReorganize?: boolean) => Promise<void>;
  addChildNode: (parentId: string, label?: string) => Promise<void>;
  updateNode: (id: string, data: Partial<MindmapNodeData>) => Promise<void>;
  deleteNode: (id: string) => Promise<void>;
  setSelectedNode: (node: Node<MindmapNodeData> | null) => void;
  
  // Actions pour les triggers
  addTrigger: (nodeId: string, trigger: TriggerCreate) => Promise<void>;
  removeTrigger: (nodeId: string, triggerId: number) => Promise<void>;
  updateTrigger: (triggerId: number, update: Partial<TriggerCreate>) => Promise<void>;
  
  // Actions pour les actions
  addAction: (triggerId: number, action: ActionCreate) => Promise<void>;
  removeAction: (actionId: number) => Promise<void>;
  
  // Traitement IA
  processText: (text: string) => Promise<void>;
  reorganizeMindmapWithAI: (focusArea?: string) => Promise<void>;
  
  // Utilitaires
  clearError: () => void;
  reorganizeGraph: () => Promise<void>;
  reset: () => void;
}

// Convertir NodeResponse en Node React Flow
const nodeResponseToFlowNode = (node: NodeResponse): Node<MindmapNodeData> => {
  // Valider et mapper le statut backend vers le type NodeStatus
  const status: NodeStatus = isValidStatus(node.status) ? node.status : 'inbox';
  
  return {
    id: `node-${node.id}`,
    type: 'mindmapNode',
    position: { x: node.position_x, y: node.position_y },
    data: {
      label: node.label,
      description: node.description || undefined,
      color: node.color,
      isRoot: node.is_root,
      status,
      backendId: node.id,
      backendParentId: node.parent_id,
      triggers: [], // Sera chargé séparément si nécessaire
    },
  };
};

// Fonction pour calculer une position hiérarchique (gauche/droite) sans chevauchement
const calculateHierarchicalPosition = (
  parentNode: Node<MindmapNodeData>,
  existingNodes: Node<MindmapNodeData>[],
  parentBackendId: number | undefined,
  nodeWidth: number = 200,
  nodeHeight: number = 100,
  horizontalSpacing: number = 280, // Distance horizontale depuis le parent
  verticalSpacing: number = 140 // Distance verticale entre nœuds au même niveau
): { x: number; y: number } => {
  const startTime = Date.now();
  console.log(`[calculateHierarchicalPosition] ⏱️ [${new Date().toISOString()}] DÉBUT - parent: ${parentNode.data.label}, nodes: ${existingNodes.length}`);
  
  try {
    // Trouver tous les nœuds enfants du parent
    const siblings = existingNodes.filter(
      n => n.data.backendParentId === parentBackendId && n.id !== parentNode.id
    );
    console.log(`[calculateHierarchicalPosition] 🔍 [${new Date().toISOString()}] Frères trouvés: ${siblings.length}`);
    
    const siblingCount = siblings.length;
    const isLeft = siblingCount % 2 === 0; // Alterner gauche/droite
    const side = isLeft ? -1 : 1; // -1 pour gauche, 1 pour droite
    console.log(`[calculateHierarchicalPosition] 📍 [${new Date().toISOString()}] Côté: ${isLeft ? 'gauche' : 'droite'} (side: ${side})`);
    
    // Calculer la position Y basée sur le nombre de nœuds existants du même côté
    const leftSiblings = siblings.filter((_, idx) => idx % 2 === 0);
    const rightSiblings = siblings.filter((_, idx) => idx % 2 === 1);
    const sameSideSiblings = isLeft ? leftSiblings : rightSiblings;
    const yOffset = (sameSideSiblings.length * verticalSpacing) - (sameSideSiblings.length * verticalSpacing / 2);
    console.log(`[calculateHierarchicalPosition] 📊 [${new Date().toISOString()}] yOffset: ${yOffset}, sameSideSiblings: ${sameSideSiblings.length}`);
    
    // Position de base
    let candidateX = parentNode.position.x + (side * horizontalSpacing);
    let candidateY = parentNode.position.y + yOffset;
    console.log(`[calculateHierarchicalPosition] 📍 [${new Date().toISOString()}] Position initiale: (${candidateX}, ${candidateY})`);
    
    // Calculer le niveau de profondeur dans la hiérarchie
    const getDepth = (nodeId: string): number => {
      let depth = 0;
      let visited = new Set<string>();
      let currentNode = existingNodes.find(n => n.id === nodeId);
      while (currentNode && currentNode.data.backendParentId) {
        if (visited.has(currentNode.id)) {
          console.warn(`[calculateHierarchicalPosition] ⚠️ Cycle détecté dans getDepth pour ${nodeId}`);
          break; // Cycle détecté
        }
        visited.add(currentNode.id);
        depth++;
        if (depth > 50) {
          console.warn(`[calculateHierarchicalPosition] ⚠️ Profondeur maximale atteinte dans getDepth`);
          break;
        }
        currentNode = existingNodes.find(n => n.data.backendId === currentNode!.data.backendParentId);
      }
      return depth;
    };
    
    const parentDepth = getDepth(parentNode.id);
    const currentDepth = parentDepth + 1;
    console.log(`[calculateHierarchicalPosition] 📊 [${new Date().toISOString()}] Profondeur: parent=${parentDepth}, courant=${currentDepth}`);
    
    // Ajuster l'espacement horizontal en fonction de la profondeur
    const adjustedHorizontalSpacing = horizontalSpacing * (0.8 + (currentDepth * 0.1));
    candidateX = parentNode.position.x + (side * adjustedHorizontalSpacing);
    console.log(`[calculateHierarchicalPosition] 📍 [${new Date().toISOString()}] Position ajustée: (${candidateX}, ${candidateY}), spacing: ${adjustedHorizontalSpacing}`);
    
    // Vérifier les chevauchements et ajuster si nécessaire
    const minDistance = Math.max(nodeWidth, nodeHeight) + 40;
    let attempts = 0;
    const maxAttempts = 20;
    console.log(`[calculateHierarchicalPosition] 🔍 [${new Date().toISOString()}] Vérification des chevauchements (${existingNodes.length} nœuds à vérifier)...`);
    
    while (attempts < maxAttempts) {
      let hasOverlap = false;
      
      for (const existingNode of existingNodes) {
        if (existingNode.id === parentNode.id) continue;
        
        const dx = Math.abs(candidateX - existingNode.position.x);
        const dy = Math.abs(candidateY - existingNode.position.y);
        
        // Vérifier le chevauchement (rectangulaire)
        if (dx < minDistance && dy < minDistance) {
          hasOverlap = true;
          break;
        }
      }
      
      if (!hasOverlap) {
        console.log(`[calculateHierarchicalPosition] ✅ [${new Date().toISOString()}] Aucun chevauchement trouvé après ${attempts} tentatives`);
        break;
      }
      
      // Ajuster verticalement en spirale
      const adjustment = (attempts + 1) * verticalSpacing;
      candidateY = parentNode.position.y + yOffset + (attempts % 2 === 0 ? adjustment : -adjustment);
      
      attempts++;
      if (attempts % 5 === 0) {
        console.log(`[calculateHierarchicalPosition] 🔄 [${new Date().toISOString()}] Tentative ${attempts}/${maxAttempts}, ajustement position...`);
      }
    }
    
    // Si toujours en chevauchement, ajuster horizontalement aussi
    if (attempts >= maxAttempts) {
      console.warn(`[calculateHierarchicalPosition] ⚠️ [${new Date().toISOString()}] Maximum d'essais atteint (${maxAttempts}), ajustement horizontal...`);
      const extraSpacing = Math.ceil(attempts / 5) * 50;
      candidateX = parentNode.position.x + (side * (adjustedHorizontalSpacing + extraSpacing));
    }
    
    const result = { x: candidateX, y: candidateY };
    console.log(`[calculateHierarchicalPosition] ✅ [${new Date().toISOString()}] FIN - Position finale: (${result.x}, ${result.y}), temps: ${Date.now() - startTime}ms`);
    return result;
  } catch (error) {
    console.error(`[calculateHierarchicalPosition] ❌ [${new Date().toISOString()}] ERREUR après ${Date.now() - startTime}ms:`, error);
    console.error(`[calculateHierarchicalPosition] Stack trace:`, error instanceof Error ? error.stack : 'N/A');
    // Retourner une position par défaut en cas d'erreur
    return { x: parentNode.position.x + 200, y: parentNode.position.y };
  }
};

// Convertir Node React Flow en NodeCreate pour l'API
const flowNodeToNodeCreate = (
  node: Node<MindmapNodeData>,
  mindmapId: number
): NodeCreate => {
  // Utiliser backendParentId si disponible (cas le plus courant)
  let parentId: number | null = null;
  
  if (node.data.backendParentId !== undefined && node.data.backendParentId !== null) {
    parentId = node.data.backendParentId;
  }

  return {
    mindmap_id: mindmapId,
    parent_id: parentId,
    label: node.data.label,
    description: node.data.description || null,
    color: node.data.color || '#00D9FF',
    position_x: Math.round(node.position.x),
    position_y: Math.round(node.position.y),
    is_root: node.data.isRoot || false,
    status: node.data.status || 'inbox',
  };
};

export const useMindmapStore = create<MindmapState>((set, get) => ({
  // État initial
  mindmaps: [],
  currentMindmap: null,
  isLoadingMindmaps: false,
  nodes: [],
  edges: [],
  selectedNode: null,
  isProcessing: false,
  isSaving: false,
  isReorganizing: false,
  isUpdatingNode: false,
  error: null,

  // Charger tous les mindmaps de l'utilisateur
  loadMindmaps: async () => {
    set({ isLoadingMindmaps: true, error: null });
    try {
      const mindmaps = await mindmapsApi.list();
      set({ mindmaps, isLoadingMindmaps: false });
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors du chargement des mindmaps';
      set({ error: errorMessage, isLoadingMindmaps: false });
    }
  },

  // Créer un nouveau mindmap
  createMindmap: async (name: string, description?: string) => {
    set({ error: null });
    try {
      const newMindmap = await mindmapsApi.create({ name, description: description || null });
      set((state) => ({ 
        mindmaps: [...state.mindmaps, newMindmap],
        currentMindmap: newMindmap,
      }));
      
      // Créer un nœud racine par défaut
      await get().loadNodes(newMindmap.id);
      return newMindmap;
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la création du mindmap';
      set({ error: errorMessage });
      return null;
    }
  },

  // Sélectionner un mindmap et charger ses nœuds
  selectMindmap: async (mindmapId: number) => {
    set({ error: null, isProcessing: true });
    try {
      const mindmapData = await mindmapsApi.get(mindmapId);
      set({ currentMindmap: mindmapData });
      await get().loadNodes(mindmapId);
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors du chargement du mindmap';
      set({ error: errorMessage, isProcessing: false });
    }
  },

  // Supprimer un mindmap
  deleteMindmap: async (mindmapId: number) => {
    set({ error: null });
    try {
      await mindmapsApi.delete(mindmapId);
      set((state) => {
        const updatedMindmaps = state.mindmaps.filter(m => m.id !== mindmapId);
        const newCurrent = state.currentMindmap?.id === mindmapId 
          ? (updatedMindmaps.length > 0 ? updatedMindmaps[0] : null)
          : state.currentMindmap;
        
        return {
          mindmaps: updatedMindmaps,
          currentMindmap: newCurrent,
          nodes: newCurrent ? state.nodes : [],
          edges: newCurrent ? state.edges : [],
        };
      });
      
      // Si un mindmap est toujours sélectionné, recharger ses nœuds
      const { currentMindmap } = get();
      if (currentMindmap) {
        await get().loadNodes(currentMindmap.id);
      }
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la suppression du mindmap';
      set({ error: errorMessage });
    }
  },

  // Mettre à jour un mindmap
  updateMindmap: async (mindmapId: number, name?: string, description?: string) => {
    set({ error: null });
    try {
      const updated = await mindmapsApi.update(mindmapId, { name, description: description || null });
      set((state) => ({
        mindmaps: state.mindmaps.map(m => m.id === mindmapId ? updated : m),
        currentMindmap: state.currentMindmap?.id === mindmapId ? updated : state.currentMindmap,
      }));
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la mise à jour du mindmap';
      set({ error: errorMessage });
    }
  },

  // Charger les nœuds d'un mindmap
  loadNodes: async (mindmapId: number) => {
    set({ isProcessing: true, error: null });
    try {
      const nodesResponse = await nodesApi.listByMindmap(mindmapId);
      console.log(`[loadNodes] ${nodesResponse.length} nœuds reçus du backend`);
      
      // Convertir en nodes React Flow
      const flowNodes: Node<MindmapNodeData>[] = nodesResponse.map(nodeResponseToFlowNode);
      
      // Créer un map pour accès rapide par backendId
      const nodesMap = new Map<number, Node<MindmapNodeData>>();
      flowNodes.forEach(n => {
        if (n.data.backendId !== undefined) {
          nodesMap.set(n.data.backendId, n);
        }
      });
      
      // Charger les triggers pour tous les nœuds en parallèle
      console.log(`[loadNodes] Chargement des triggers pour ${flowNodes.length} nœuds...`);
      const triggersPromises = flowNodes
        .filter(n => n.data.backendId !== undefined)
        .map(async (node) => {
          try {
            const triggers = await triggersApi.listByNode(node.data.backendId!);
            return { nodeId: node.id, backendId: node.data.backendId!, triggers };
          } catch (error) {
            console.error(`[loadNodes] Erreur lors du chargement des triggers pour le nœud ${node.id}:`, error);
            return { nodeId: node.id, backendId: node.data.backendId!, triggers: [] };
          }
        });
      
      const triggersResults = await Promise.all(triggersPromises);
      console.log(`[loadNodes] Triggers chargés pour ${triggersResults.length} nœuds`);
      
      // Mettre à jour les nœuds avec leurs triggers
      const nodesWithTriggers = flowNodes.map(node => {
        const triggersResult = triggersResults.find(r => r.nodeId === node.id);
        if (triggersResult) {
          return {
            ...node,
            data: {
              ...node.data,
              triggers: triggersResult.triggers,
            },
          };
        }
        return node;
      });
      
      // Créer les edges à partir de la hiérarchie avec les handles corrects
      // Utiliser un Set pour éviter les doublons
      const edgeIds = new Set<string>();
      const flowEdges: Edge[] = [];
      
      nodesWithTriggers.forEach((node) => {
        const parentBackendId = node.data.backendParentId;
        
        if (parentBackendId !== null && parentBackendId !== undefined) {
          const parentNode = nodesMap.get(parentBackendId);
          
          if (parentNode) {
            const edgeId = `edge-${parentNode.id}-${node.id}`;
            
            // Éviter les doublons
            if (!edgeIds.has(edgeId)) {
              edgeIds.add(edgeId);
              
              // Utiliser la fonction qui minimise la distance entre les nœuds
              const { sourceHandle, targetHandle } = findOptimalHandles(
                parentNode.position,
                node.position
              );
              
              flowEdges.push({
                id: edgeId,
                source: parentNode.id,
                target: node.id,
                sourceHandle,
                targetHandle,
                type: 'smoothstep',
                animated: false,
                style: { 
                  stroke: node.data.color || '#00D9FF', 
                  strokeWidth: 2 
                },
              });
            } else {
              console.warn(`[loadNodes] Edge dupliqué évité: ${edgeId}`);
            }
          } else {
            console.warn(`[loadNodes] Parent non trouvé pour nœud ${node.id} (backendParentId=${parentBackendId})`);
          }
        }
      });
      
      console.log(`[loadNodes] ${flowEdges.length} edges créés`);
      
      set({ nodes: nodesWithTriggers, edges: flowEdges, isProcessing: false });
      
      // Réorganiser automatiquement le graphe après le chargement
      setTimeout(async () => {
        await get().reorganizeGraph();
      }, 200);
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors du chargement des nœuds';
      set({ error: errorMessage, isProcessing: false });
    }
  },

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),

  // Mettre à jour les handles des edges pour minimiser la distance
  updateEdgesHandles: () => {
    const state = get();
    const { nodes, edges } = state;
    
    if (nodes.length === 0 || edges.length === 0) {
      return;
    }
    
    // Créer un map des positions des nœuds
    const nodePositions = new Map<string, { x: number; y: number }>();
    nodes.forEach((n) => nodePositions.set(n.id, n.position));
    
    // Recalculer les handles pour tous les edges
    const updatedEdges = edges.map((edge) => {
      const sourcePos = nodePositions.get(edge.source);
      const targetPos = nodePositions.get(edge.target);
      
      if (!sourcePos || !targetPos) {
        return edge;
      }
      
      // Utiliser la fonction qui minimise la distance entre les nœuds
      const { sourceHandle, targetHandle } = findOptimalHandles(
        sourcePos,
        targetPos
      );
      
      return {
        ...edge,
        sourceHandle,
        targetHandle,
      };
    });
    
    set({ edges: updatedEdges });
  },

  // Ajouter un nœud (sauvegarder sur le backend)
  addNode: async (node: Node<MindmapNodeData>, skipReorganize: boolean = false) => {
    const startTime = Date.now();
    console.log(`[addNode] ⏱️ [${new Date().toISOString()}] DÉBUT - label: "${node.data.label}", skipReorganize: ${skipReorganize}`);
    
    const { currentMindmap, nodes, isSaving, isReorganizing } = get();
    console.log(`[addNode] État initial - isSaving: ${isSaving}, isReorganizing: ${isReorganizing}, nodes count: ${nodes.length}`);
    
    if (!currentMindmap) {
      console.error(`[addNode] ❌ [${new Date().toISOString()}] Aucun mindmap sélectionné`);
      set({ error: 'Aucun mindmap sélectionné' });
      return;
    }

    console.log(`[addNode] 🔄 [${new Date().toISOString()}] Définition de isSaving=true...`);
    set({ isSaving: true, error: null });
    
    try {
      // Si le nœud a un parent, recalculer sa position avec le layout hiérarchique
      let finalNode = node;
      if (node.data.backendParentId) {
        console.log(`[addNode] 🔍 [${new Date().toISOString()}] Recherche du parent (backendId: ${node.data.backendParentId})...`);
        const parentNode = nodes.find(n => n.data.backendId === node.data.backendParentId);
        if (parentNode) {
          console.log(`[addNode] ✅ [${new Date().toISOString()}] Parent trouvé: ${parentNode.data.label}, calcul de la position...`);
          console.log(`[addNode] 🔄 [${new Date().toISOString()}] Appel de calculateHierarchicalPosition...`);
          const calculatedPosition = calculateHierarchicalPosition(
            parentNode,
            nodes,
            node.data.backendParentId
          );
          console.log(`[addNode] ✅ [${new Date().toISOString()}] Position calculée retournée: (${calculatedPosition.x}, ${calculatedPosition.y})`);
          finalNode = {
            ...node,
            position: calculatedPosition,
          };
          console.log(`[addNode] ✅ [${new Date().toISOString()}] finalNode créé avec position`);
        } else {
          console.warn(`[addNode] ⚠️ [${new Date().toISOString()}] Parent non trouvé pour backendId: ${node.data.backendParentId}`);
        }
      } else {
        console.log(`[addNode] 📍 [${new Date().toISOString()}] Pas de parent, utilisation de la position du nœud: (${node.position.x}, ${node.position.y})`);
      }
      
      console.log(`[addNode] 🔄 [${new Date().toISOString()}] Conversion en NodeCreate...`);
      const nodeCreate = flowNodeToNodeCreate(finalNode, currentMindmap.id);
      console.log(`[addNode] ✅ [${new Date().toISOString()}] NodeCreate créé`);
      console.log(`[addNode] 📤 [${new Date().toISOString()}] Envoi de la requête API de création...`);
      console.log(`[addNode] Payload:`, JSON.stringify(nodeCreate, null, 2));
      
      console.log(`[addNode] ⏳ [${new Date().toISOString()}] Attente de la réponse API...`);
      const createdNode = await nodesApi.create(nodeCreate);
      console.log(`[addNode] ✅ [${new Date().toISOString()}] Nœud créé sur le backend:`, createdNode);
      
      // Mettre à jour le nœud avec l'ID backend
      const newNodeId = `node-${createdNode.id}`;
      const updatedNode: Node<MindmapNodeData> = {
        ...finalNode,
        id: newNodeId,
        data: {
          ...finalNode.data,
          backendId: createdNode.id,
          backendParentId: createdNode.parent_id,
        },
      };

      console.log(`[addNode] 🔗 [${new Date().toISOString()}] Mise à jour des edges...`);
      console.log(`[addNode] 📋 [${new Date().toISOString()}] Nouveau nœud - id: ${newNodeId}, backendId: ${createdNode.id}, parent_id: ${createdNode.parent_id}`);
      
      // Mettre à jour les edges si nécessaire
      // Supprimer d'abord tous les edges qui pointent vers l'ancien ID (si le nœud avait un ID temporaire)
      let newEdges = get().edges.filter(e => e.target !== finalNode.id && e.source !== finalNode.id);
      console.log(`[addNode] 🧹 [${new Date().toISOString()}] Ancien edges nettoyés, reste: ${newEdges.length} edges`);
      
      if (createdNode.parent_id) {
        const parentId = `node-${createdNode.parent_id}`;
        const currentState = get();
        const parentNode = currentState.nodes.find(n => n.id === parentId);
        console.log(`[addNode] 🔍 [${new Date().toISOString()}] Recherche du parent - parentId: ${parentId}, found: ${!!parentNode}`);
        
        const edgeExists = newEdges.some(
          e => e.source === parentId && e.target === newNodeId
        );
        console.log(`[addNode] 🔍 [${new Date().toISOString()}] Edge existe déjà: ${edgeExists}`);
        
        if (!edgeExists && parentNode) {
          // Utiliser la fonction qui minimise la distance entre les nœuds
          const { sourceHandle, targetHandle } = findOptimalHandles(
            parentNode.position,
            updatedNode.position
          );
          
          const newEdge = {
            id: `edge-${parentId}-${newNodeId}`,
            source: parentId,
            target: newNodeId,
            sourceHandle,
            targetHandle,
            type: 'smoothstep',
            animated: false, // Désactiver l'animation pour éviter les problèmes visuels
            style: { 
              stroke: updatedNode.data.color || '#00D9FF', 
              strokeWidth: 2 
            },
          };
          
          newEdges.push(newEdge);
          console.log(`[addNode] ✅ [${new Date().toISOString()}] Edge créé: ${parentId} -> ${newNodeId}, style: ${JSON.stringify(newEdge.style)}`);
        } else {
          console.log(`[addNode] ⏭️ [${new Date().toISOString()}] Edge ignoré - exists: ${edgeExists}, parentNode: ${!!parentNode}`);
        }
      } else {
        console.log(`[addNode] ℹ️ [${new Date().toISOString()}] Pas de parent_id, pas d'edge à créer`);
      }

      console.log(`[addNode] 💾 [${new Date().toISOString()}] Mise à jour du store...`);
      console.log(`[addNode] 📋 [${new Date().toISOString()}] Données à sauvegarder - nodes: 1 nouveau (${newNodeId}), edges: ${newEdges.length}`);
      
      set((state) => {
        // Filtrer le nœud s'il existe déjà avec l'ancien ID (ID temporaire)
        const existingNodeIndex = state.nodes.findIndex(n => 
          (n.data.backendId === createdNode.id) || 
          (n.id === finalNode.id && finalNode.id !== newNodeId)
        );
        
        let updatedNodes: Node<MindmapNodeData>[];
        if (existingNodeIndex >= 0) {
          console.log(`[addNode] 🔄 [${new Date().toISOString()}] Remplacement du nœud existant à l'index ${existingNodeIndex}`);
          updatedNodes = [...state.nodes];
          updatedNodes[existingNodeIndex] = updatedNode;
        } else {
          updatedNodes = [...state.nodes, updatedNode];
        }
        
        console.log(`[addNode] ✅ [${new Date().toISOString()}] Store mis à jour - nodes: ${updatedNodes.length} (ajout: ${existingNodeIndex < 0 ? 'oui' : 'remplacement'}), edges: ${newEdges.length}`);
        console.log(`[addNode] 📋 [${new Date().toISOString()}] IDs des nœuds:`, updatedNodes.map(n => ({ id: n.id, backendId: n.data.backendId, label: n.data.label })));
        console.log(`[addNode] 🔗 [${new Date().toISOString()}] IDs des edges:`, newEdges.map(e => ({ id: e.id, source: e.source, target: e.target })));
        
        return {
          nodes: updatedNodes,
          edges: newEdges,
          isSaving: false,
        };
      });

      // Réorganiser automatiquement le graphe après l'ajout (sauf si skipReorganize est true)
      if (!skipReorganize) {
        console.log(`[addNode] 🔄 [${new Date().toISOString()}] skipReorganize=false, planification de reorganizeGraph...`);
        setTimeout(async () => {
          console.log(`[addNode] 🔄 [${new Date().toISOString()}] Exécution de reorganizeGraph (timeout)...`);
          await get().reorganizeGraph();
          console.log(`[addNode] ✅ [${new Date().toISOString()}] reorganizeGraph terminé (temps total: ${Date.now() - startTime}ms)`);
        }, 100);
      } else {
        console.log(`[addNode] ⏭️ [${new Date().toISOString()}] skipReorganize=true, réorganisation ignorée (temps total: ${Date.now() - startTime}ms)`);
      }
    } catch (error) {
      console.error(`[addNode] ❌ [${new Date().toISOString()}] ERREUR après ${Date.now() - startTime}ms:`, error);
      console.error(`[addNode] Stack trace:`, error instanceof Error ? error.stack : 'N/A');
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la création du nœud';
      set({ error: errorMessage, isSaving: false });
    }
  },

  // Ajouter un nœud enfant à un nœud parent
  addChildNode: async (parentId: string, label?: string) => {
    const startTime = Date.now();
    console.log(`[addChildNode] ⏱️ [${new Date().toISOString()}] DÉBUT - parentId: ${parentId}, label: ${label}`);
    
    const { nodes, currentMindmap, isSaving, isReorganizing } = get();
    console.log(`[addChildNode] État initial - isSaving: ${isSaving}, isReorganizing: ${isReorganizing}, nodes count: ${nodes.length}, mindmap: ${currentMindmap?.id}`);
    
    // Empêcher les appels multiples simultanés
    if (isSaving || isReorganizing) {
      console.warn(`[addChildNode] ⚠️ [${new Date().toISOString()}] BLOCQUÉ - Une opération est déjà en cours (isSaving: ${isSaving}, isReorganizing: ${isReorganizing})`);
      return;
    }
    
    if (!currentMindmap) {
      console.error(`[addChildNode] ❌ [${new Date().toISOString()}] Aucun mindmap sélectionné`);
      set({ error: 'Aucun mindmap sélectionné' });
      return;
    }

    // Trouver le nœud parent
    const parentNode = nodes.find(n => n.id === parentId);
    if (!parentNode || !parentNode.data.backendId) {
      console.error(`[addChildNode] ❌ [${new Date().toISOString()}] Nœud parent introuvable - parentId: ${parentId}, found: ${!!parentNode}, backendId: ${parentNode?.data.backendId}`);
      set({ error: 'Nœud parent introuvable' });
      return;
    }

    console.log(`[addChildNode] ✅ [${new Date().toISOString()}] Parent trouvé: ${parentNode.data.label} (backendId: ${parentNode.data.backendId})`);

    try {
      // Créer le nœud enfant avec le parent comme parent
      const childLabel = label || `Sous-nœud de ${parentNode.data.label}`;
      const childNode: Node<MindmapNodeData> = {
        id: `node-temp-${Date.now()}`,
        position: { x: 0, y: 0 }, // La position sera calculée par addNode
        type: 'mindmapNode',
        data: {
          label: childLabel,
          description: '',
          color: parentNode.data.color || '#00D9FF',
          isRoot: false,
          status: 'inbox',
          backendParentId: parentNode.data.backendId,
        },
      };

      console.log(`[addChildNode] 📝 [${new Date().toISOString()}] Création du nœud enfant: "${childLabel}" sous parent: "${parentNode.data.label}"`);

      // Utiliser addNode pour créer le nœud enfant (qui calculera automatiquement la position)
      // addNode gère déjà isSaving, donc ne pas le définir ici
      // Désactiver la réorganisation automatique pour éviter les scintillements
      console.log(`[addChildNode] 🔄 [${new Date().toISOString()}] Appel de addNode avec skipReorganize=true...`);
      await get().addNode(childNode, true);
      console.log(`[addChildNode] ✅ [${new Date().toISOString()}] addNode terminé (temps: ${Date.now() - startTime}ms)`);
      
      // Attendre un peu pour que le nœud soit complètement créé et dans le store
      console.log(`[addChildNode] ⏳ [${new Date().toISOString()}] Attente de 300ms pour synchronisation...`);
      await new Promise(resolve => setTimeout(resolve, 300));
      console.log(`[addChildNode] ✅ [${new Date().toISOString()}] Attente terminée`);
      
      // Faire une seule réorganisation à la fin, seulement si le nœud a été créé
      const stateAfterAdd = get();
      console.log(`[addChildNode] 🔍 [${new Date().toISOString()}] Recherche du nœud créé dans le store (nodes count: ${stateAfterAdd.nodes.length})...`);
      const createdNode = stateAfterAdd.nodes.find(
        n => n.data.backendParentId === parentNode.data.backendId && n.data.label === childLabel
      );
      
      // Attendre que isSaving soit false (addNode termine)
      console.log(`[addChildNode] ⏳ [${new Date().toISOString()}] Attente que isSaving soit false...`);
      let attempts = 0;
      while (get().isSaving && attempts < 15) {
        console.log(`[addChildNode] ⏳ [${new Date().toISOString()}] Tentative ${attempts + 1}/15 - isSaving: ${get().isSaving}, isReorganizing: ${get().isReorganizing}`);
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
      }
      
      // Vérifier que le nœud a bien été créé dans le store
      const stateAfterWait = get();
      console.log(`[addChildNode] 🔍 [${new Date().toISOString()}] Vérification du nœud créé (nodes count: ${stateAfterWait.nodes.length})...`);
      const createdNodeAfterWait = stateAfterWait.nodes.find(
        n => n.data.backendParentId === parentNode.data.backendId && n.data.label === childLabel
      );
      
      if (createdNodeAfterWait) {
        console.log(`[addChildNode] ✅ [${new Date().toISOString()}] Nœud confirmé dans le store: ${createdNodeAfterWait.id} (backendId: ${createdNodeAfterWait.data.backendId})`);
        console.log(`[addChildNode] 📍 [${new Date().toISOString()}] Position du nœud: (${createdNodeAfterWait.position.x}, ${createdNodeAfterWait.position.y})`);
        
        // Vérifier que le lien existe
        const edgeExists = stateAfterWait.edges.some(
          e => e.target === createdNodeAfterWait.id || e.source === createdNodeAfterWait.id
        );
        console.log(`[addChildNode] 🔗 [${new Date().toISOString()}] Lien existe: ${edgeExists}, edges count: ${stateAfterWait.edges.length}`);
        
        if (!edgeExists && createdNodeAfterWait.data.backendParentId) {
          console.warn(`[addChildNode] ⚠️ [${new Date().toISOString()}] Lien manquant, vérification...`);
          // Le lien devrait être créé par addNode ou loadNodes
        }
      } else {
        console.warn(`[addChildNode] ⚠️ [${new Date().toISOString()}] Nœud non trouvé dans le store après attente`);
        console.warn(`[addChildNode] Nœuds avec même parent_id (${parentNode.data.backendId}):`, 
          stateAfterWait.nodes.filter(n => n.data.backendParentId === parentNode.data.backendId).map(n => ({ id: n.id, label: n.data.label, backendId: n.data.backendId }))
        );
        console.warn(`[addChildNode] Tous les nœuds:`, stateAfterWait.nodes.map(n => ({ id: n.id, label: n.data.label, backendId: n.data.backendId, parentId: n.data.backendParentId })));
        
        // En dernier recours, recharger depuis le backend
        console.log(`[addChildNode] 🔄 [${new Date().toISOString()}] Rechargement depuis le backend en dernier recours...`);
        await get().loadNodes(currentMindmap.id);
      }
      
      // Attendre que la réorganisation soit terminée (si elle est en cours)
      attempts = 0;
      while (get().isReorganizing && attempts < 20) {
        console.log(`[addChildNode] ⏳ [${new Date().toISOString()}] Attente fin réorganisation ${attempts + 1}/20...`);
        await new Promise(resolve => setTimeout(resolve, 200));
        attempts++;
      }
      
      console.log(`[addChildNode] ✅ [${new Date().toISOString()}] FIN (temps total: ${Date.now() - startTime}ms)`);
    } catch (error) {
      console.error(`[addChildNode] ❌ [${new Date().toISOString()}] ERREUR après ${Date.now() - startTime}ms:`, error);
      console.error(`[addChildNode] Stack trace:`, error instanceof Error ? error.stack : 'N/A');
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la création du sous-nœud';
      set({ error: errorMessage, isSaving: false, isReorganizing: false });
    }
  },

  // Mettre à jour un nœud
  updateNode: async (id: string, data: Partial<MindmapNodeData>) => {
    const backendId = parseInt(id.replace('node-', ''));
    if (isNaN(backendId)) {
      // Nœud local non encore sauvegardé
      set((state) => ({
        nodes: state.nodes.map((node) =>
          node.id === id ? { ...node, data: { ...node.data, ...data } } : node
        ),
      }));
      return;
    }

    set({ isSaving: true, isUpdatingNode: true, error: null });
    try {
      const nodeUpdate: any = {};
      if (data.label !== undefined) nodeUpdate.label = data.label;
      if (data.description !== undefined) nodeUpdate.description = data.description;
      if (data.color !== undefined) nodeUpdate.color = data.color;
      if (data.status !== undefined) nodeUpdate.status = data.status;
      if (data.backendParentId !== undefined) nodeUpdate.parent_id = data.backendParentId;

      // Mettre à jour les positions si le nœud a changé
      const currentNodes = get().nodes;
      const currentNode = currentNodes.find(n => n.id === id);
      if (currentNode) {
        nodeUpdate.position_x = Math.round(currentNode.position.x);
        nodeUpdate.position_y = Math.round(currentNode.position.y);
      }

      await nodesApi.update(backendId, nodeUpdate);

      set((state) => {
        const updatedNodes = state.nodes.map((node) =>
          node.id === id ? { ...node, data: { ...node.data, ...data } } : node
        );
        // Mettre à jour aussi selectedNode si c'est le nœud modifié
        const updatedSelectedNode = state.selectedNode?.id === id
          ? updatedNodes.find(n => n.id === id) || null
          : state.selectedNode;
        
        return {
          nodes: updatedNodes,
          selectedNode: updatedSelectedNode,
          isSaving: false,
          isUpdatingNode: false,
        };
      });
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la mise à jour du nœud';
      set({ error: errorMessage, isSaving: false, isUpdatingNode: false });
    }
  },

  // Supprimer un nœud
  deleteNode: async (id: string) => {
    console.log('deleteNode called for:', id);
    
    // Trouver le nœud dans le store pour vérifier son backendId
    const state = get();
    const nodeToDelete = state.nodes.find(n => n.id === id);
    
    if (!nodeToDelete) {
      console.error('Node not found in store:', id);
      set({ error: 'Nœud introuvable' });
      return;
    }
    
    // Utiliser directement backendId s'il existe, sinon extraire de l'ID
    let backendId: number | null = null;
    
    if (nodeToDelete.data.backendId) {
      backendId = nodeToDelete.data.backendId;
    } else if (id.startsWith('node-')) {
      backendId = parseInt(id.replace('node-', ''));
    }
    
    console.log('Node to delete:', { id, backendId, hasBackendId: !!nodeToDelete.data.backendId });
    
    if (!backendId || isNaN(backendId)) {
      console.log('Local node, deleting from state only');
      // Nœud local non encore sauvegardé
      set({
        nodes: state.nodes.filter((node) => node.id !== id),
        edges: state.edges.filter((edge) => edge.source !== id && edge.target !== id),
        selectedNode: state.selectedNode?.id === id ? null : state.selectedNode,
      });
      console.log('Local node deleted, remaining nodes:', get().nodes.length);
      
      // Réorganiser automatiquement le graphe après la suppression
      setTimeout(async () => {
        await get().reorganizeGraph();
      }, 100);
      return;
    }

    set({ error: null, isSaving: true });
    try {
      console.log('Deleting node from backend:', backendId);
      const result = await nodesApi.delete(backendId);
      console.log('Node deleted from backend successfully, result:', result);
      
      // Désélectionner le nœud si c'est celui qu'on supprime
      if (state.selectedNode?.id === id) {
        set({ selectedNode: null });
      }
      
      // Recharger TOUS les nœuds depuis le backend pour avoir l'état correct
      // (enfants réassignés, etc.)
      const { currentMindmap } = get();
      if (currentMindmap) {
        console.log('Reloading nodes from backend after deletion');
        await get().loadNodes(currentMindmap.id);
      }
      
      set({ isSaving: false });
    } catch (error) {
      console.error('Error deleting node:', error);
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la suppression du nœud';
      set({ error: errorMessage, isSaving: false });
    }
  },

  setSelectedNode: (node) => set({ selectedNode: node }),

  // Ajouter un trigger
  addTrigger: async (nodeId: string, trigger: TriggerCreate) => {
    console.log('addTrigger called for node:', nodeId, trigger);
    const backendNodeId = parseInt(nodeId.replace('node-', ''));
    if (isNaN(backendNodeId)) {
      console.error('Node not saved yet');
      set({ error: 'Nœud non sauvegardé. Enregistrez d\'abord le nœud.' });
      return;
    }

    set({ error: null, isSaving: true });
    try {
      console.log('Creating trigger on backend for node:', backendNodeId);
      const createdTrigger = await triggersApi.create({
        ...trigger,
        node_id: backendNodeId,
      });
      console.log('Trigger created:', createdTrigger);

      set((state) => {
        console.log('[mindmapStore] Avant mise à jour - nodes:', state.nodes.map(n => ({ id: n.id, triggersCount: n.data?.triggers?.length || 0 })));
        const updatedNodes = state.nodes.map((node) =>
          node.id === nodeId
            ? {
                ...node,
                data: {
                  ...node.data,
                  triggers: [...(node.data.triggers || []), createdTrigger],
                },
              }
            : node
        );
        console.log('[mindmapStore] Après mise à jour - nodes:', updatedNodes.map(n => ({ id: n.id, triggersCount: n.data?.triggers?.length || 0 })));
        const updatedNode = updatedNodes.find(n => n.id === nodeId);
        console.log('[mindmapStore] Node mis à jour:', updatedNode?.id, 'triggers:', updatedNode?.data?.triggers);
        return {
          nodes: updatedNodes,
          isSaving: false,
        };
      });
    } catch (error) {
      console.error('Error creating trigger:', error);
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la création du trigger';
      set({ error: errorMessage, isSaving: false });
    }
  },

  // Supprimer un trigger
  removeTrigger: async (nodeId: string, triggerId: number) => {
    console.log('removeTrigger called for node:', nodeId, 'trigger:', triggerId);
    set({ error: null, isSaving: true });
    try {
      console.log('Deleting trigger from backend:', triggerId);
      await triggersApi.delete(triggerId);
      console.log('Trigger deleted, updating state');
      set((state) => {
        console.log('[mindmapStore] Avant suppression - nodes:', state.nodes.map(n => ({ id: n.id, triggersCount: n.data?.triggers?.length || 0 })));
        const nodeToUpdate = state.nodes.find(n => n.id === nodeId);
        console.log('[mindmapStore] Node à mettre à jour:', nodeToUpdate?.id, 'triggers actuels:', nodeToUpdate?.data?.triggers);
        
        // Créer une nouvelle référence du tableau nodes
        const updatedNodes = state.nodes.map((node) => {
          if (node.id === nodeId) {
            const filteredTriggers = (node.data.triggers || []).filter((t) => {
              const shouldKeep = t.id !== triggerId;
              console.log('[mindmapStore] Trigger:', t.id, 'shouldKeep:', shouldKeep, 'triggerId à supprimer:', triggerId);
              return shouldKeep;
            });
            // Créer une nouvelle référence pour le node et ses données
            return {
              ...node,
              data: {
                ...node.data,
                triggers: filteredTriggers, // Nouveau tableau
              },
            };
          }
          return node; // Garder la même référence pour les autres nodes
        });
        
        console.log('[mindmapStore] Après suppression - nodes:', updatedNodes.map(n => ({ id: n.id, triggersCount: n.data?.triggers?.length || 0 })));
        const updatedNode = updatedNodes.find(n => n.id === nodeId);
        console.log('[mindmapStore] Node mis à jour:', updatedNode?.id, 'triggers:', updatedNode?.data?.triggers);
        console.log('[mindmapStore] Référence nodes changée?', state.nodes !== updatedNodes);
        console.log('[mindmapStore] Référence node.data changée?', nodeToUpdate?.data !== updatedNode?.data);
        console.log('[mindmapStore] Référence triggers changée?', nodeToUpdate?.data?.triggers !== updatedNode?.data?.triggers);
        
        return {
          nodes: updatedNodes, // Nouveau tableau
          isSaving: false,
        };
      });
    } catch (error) {
      console.error('Error deleting trigger:', error);
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la suppression du trigger';
      set({ error: errorMessage, isSaving: false });
    }
  },

  // Mettre à jour un trigger
  updateTrigger: async (triggerId: number, update: Partial<TriggerCreate>) => {
    set({ error: null, isSaving: true });
    try {
      await triggersApi.update(triggerId, update as any);
      set((state) => ({
        nodes: state.nodes.map((node) => {
          const triggers = (node.data.triggers || []).map((t) =>
            t.id === triggerId ? { ...t, ...update } : t
          );
          return { ...node, data: { ...node.data, triggers } };
        }),
        isSaving: false,
      }));
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la mise à jour du trigger';
      set({ error: errorMessage, isSaving: false });
    }
  },

  // Ajouter une action
  addAction: async (triggerId: number, action: ActionCreate) => {
    set({ error: null, isSaving: true });
    try {
      await actionsApi.create({ ...action, trigger_id: triggerId });
      // Les actions seront rechargées lors de la récupération du trigger
      set({ isSaving: false });
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la création de l\'action';
      set({ error: errorMessage, isSaving: false });
    }
  },

  // Supprimer une action
  removeAction: async (actionId: number) => {
    set({ error: null, isSaving: true });
    try {
      await actionsApi.delete(actionId);
      set({ isSaving: false });
    } catch (error) {
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la suppression de l\'action';
      set({ error: errorMessage, isSaving: false });
    }
  },

  // Traitement IA (génération de nœuds depuis texte via agent Agno)
  processText: async (text: string) => {
    console.log('processText called with text:', text);
    const { currentMindmap, nodes } = get();
    if (!currentMindmap) {
      console.error('No mindmap selected');
      set({ error: 'Aucun mindmap sélectionné' });
      return;
    }

    console.log('Current mindmap:', currentMindmap.id);
    console.log('Current nodes:', nodes.length);
    set({ isProcessing: true, error: null });

    try {
      // S'il n'y a pas de nœud racine, en créer un d'abord
      let rootNode = nodes.find((n) => n.data.isRoot);
      
      if (!rootNode || !rootNode.data.backendId) {
        // Créer un nœud racine si aucun n'existe
        const rootNodeData: Node<MindmapNodeData> = {
          id: `node-root-${Date.now()}`,
          type: 'mindmapNode',
          position: { x: 400, y: 300 },
          data: {
            label: currentMindmap.name,
            description: currentMindmap.description || undefined,
            color: '#00D9FF',
            isRoot: true,
            status: 'inbox',
          },
        };
        
        await get().addNode(rootNodeData, true);
        
        // Récupérer le nœud racine créé depuis le store mis à jour
        const updatedNodesAfterRoot = get().nodes;
        rootNode = updatedNodesAfterRoot.find((n) => n.data.isRoot);
        
        if (!rootNode || !rootNode.data.backendId) {
          set({ isProcessing: false, error: 'Erreur lors de la création du nœud racine' });
          return;
        }
      }

      // Appeler l'agent IA pour organiser le texte
      const response = await agentsApi.organizeText({
        mindmap_id: currentMindmap.id,
        text: text,
        auto_apply: true,
      });

      console.log('Agent response:', response);

      if (!response.success) {
        set({ error: response.message || 'Erreur lors du traitement IA', isProcessing: false });
        return;
      }

      // Recharger les nœuds pour avoir les nouveaux nœuds créés par l'agent
      await get().loadNodes(currentMindmap.id);
      
      // Réorganiser le graphe après l'ajout des nœuds
      await get().reorganizeGraph();
      
      set({ isProcessing: false });
    } catch (error) {
      console.error('Erreur dans processText:', error);
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors du traitement IA';
      set({ error: errorMessage, isProcessing: false });
    }
  },

  clearError: () => set({ error: null }),
  
  // Réorganiser le mindmap avec l'agent IA
  reorganizeMindmapWithAI: async (focusArea?: string) => {
    const { currentMindmap } = get();
    if (!currentMindmap) {
      set({ error: 'Aucun mindmap sélectionné' });
      return;
    }

    set({ isProcessing: true, error: null });

    try {
      // Appeler l'agent IA pour réorganiser le mindmap
      const response = await agentsApi.reorganizeMindmap({
        mindmap_id: currentMindmap.id,
        auto_apply: true,
        focus_area: focusArea,
      });

      console.log('Reorganize agent response:', response);

      if (!response.success) {
        set({ error: response.message || 'Erreur lors de la réorganisation IA', isProcessing: false });
        return;
      }

      // Recharger les nœuds pour avoir les modifications appliquées par l'agent
      await get().loadNodes(currentMindmap.id);
      
      // Réorganiser le graphe visuellement après les modifications
      await get().reorganizeGraph();
      
      set({ isProcessing: false });
    } catch (error) {
      console.error('Erreur dans reorganizeMindmapWithAI:', error);
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la réorganisation IA';
      set({ error: errorMessage, isProcessing: false });
    }
  },
  
  // Réorganiser le graphe avec layout ELK (Eclipse Layout Kernel)
  // Utilise l'algorithme "layered" basé sur Sugiyama, optimisé pour les arbres hiérarchiques
  reorganizeGraph: async () => {
    const startTime = Date.now();
    console.log(`[reorganizeGraph] ⏱️ [${new Date().toISOString()}] DÉBUT`);
    
    const { nodes, edges, currentMindmap, isReorganizing, isUpdatingNode, isSaving } = get();
    console.log(`[reorganizeGraph] État initial - nodes: ${nodes.length}, edges: ${edges.length}, mindmap: ${currentMindmap?.id}, isReorganizing: ${isReorganizing}, isUpdatingNode: ${isUpdatingNode}, isSaving: ${isSaving}`);
    
    if (!currentMindmap || nodes.length === 0) {
      console.log(`[reorganizeGraph] ⏭️ [${new Date().toISOString()}] Ignoré - mindmap: ${!!currentMindmap}, nodes: ${nodes.length}`);
      return;
    }

    // Éviter les réorganisations multiples simultanées
    if (isReorganizing) {
      console.log(`[reorganizeGraph] ⏭️ [${new Date().toISOString()}] Ignoré - Réorganisation déjà en cours`);
      return;
    }

    // Éviter les réorganisations pendant une mise à jour de nœud
    if (isUpdatingNode) {
      console.log(`[reorganizeGraph] ⏭️ [${new Date().toISOString()}] Ignoré - Mise à jour de nœud en cours`);
      return;
    }

    console.log(`[reorganizeGraph] 🔄 [${new Date().toISOString()}] Définition de isSaving=true, isReorganizing=true...`);
    set({ isSaving: true, isReorganizing: true, error: null });

    try {
      // Utiliser le layout bidirectionnel ELK (branches à gauche et à droite de la racine)
      // Utiliser des dimensions plus grandes pour tenir compte du titre + description
      console.log(`[reorganizeGraph] 🧮 [${new Date().toISOString()}] Calcul du layout ELK...`);
      const { nodes: layoutedNodes, edges: layoutedEdges } = await calculateBidirectionalLayout(
        nodes,
        edges,
        200, // Largeur des nœuds (augmentée pour le contenu)
        120  // Hauteur des nœuds (augmentée pour titre + description)
      );
      console.log(`[reorganizeGraph] ✅ [${new Date().toISOString()}] Layout calculé - nodes: ${layoutedNodes.length}, edges: ${layoutedEdges.length}`);
      
      // Vérifier que tous les nœuds d'origine ont été inclus dans le layout
      const originalNodeIds = new Set(nodes.map(n => n.id));
      const layoutedNodeIds = new Set(layoutedNodes.map(n => n.id));
      const missingNodeIds = nodes.filter(n => !layoutedNodeIds.has(n.id));
      
      if (missingNodeIds.length > 0) {
        console.warn(`[reorganizeGraph] ⚠️ [${new Date().toISOString()}] ${missingNodeIds.length} nœuds manquants dans le layout:`, 
          missingNodeIds.map(n => ({ id: n.id, label: n.data.label, backendId: n.data.backendId }))
        );
        console.warn(`[reorganizeGraph] Vérification dans calculateBidirectionalLayout nécessaire`);
      } else {
        console.log(`[reorganizeGraph] ✅ [${new Date().toISOString()}] Tous les nœuds (${nodes.length}) sont inclus dans le layout`);
      }

      // Mettre à jour le store avec les nouvelles positions et edges avec handles corrects
      console.log(`[reorganizeGraph] 💾 [${new Date().toISOString()}] Mise à jour du store avec les nouvelles positions...`);
      console.log(`[reorganizeGraph] 📊 Avant: ${nodes.length} nœuds, Après: ${layoutedNodes.length} nœuds`);
      // Mettre isReorganizing à false pour permettre la synchronisation des nœuds vers ReactFlow
      set({ nodes: layoutedNodes, edges: layoutedEdges, isSaving: true, isReorganizing: false });

      // Sauvegarder les nouvelles positions sur le backend
      // Collecter les IDs des nœuds qui n'existent plus sur le backend (404)
      const nodesToRemove: string[] = [];
      const nodesToUpdate = layoutedNodes.filter(n => n.data.backendId);
      console.log(`[reorganizeGraph] 📤 [${new Date().toISOString()}] Mise à jour de ${nodesToUpdate.length} nœuds sur le backend...`);
      
      const updatePromises = nodesToUpdate.map(async (node, index) => {
        if (node.data.backendId) {
          try {
            if (index % 10 === 0) {
              console.log(`[reorganizeGraph] 📤 [${new Date().toISOString()}] Mise à jour ${index + 1}/${nodesToUpdate.length}...`);
            }
            await nodesApi.update(node.data.backendId, {
              position_x: Math.round(node.position.x),
              position_y: Math.round(node.position.y),
            });
          } catch (error) {
            // Si le nœud n'existe plus sur le backend (404), le marquer pour suppression
            if (error instanceof ApiErrorResponse && error.status === 404) {
              console.warn(`[reorganizeGraph] ⚠️ [${new Date().toISOString()}] Nœud ${node.id} (backendId: ${node.data.backendId}) introuvable sur le backend, suppression du store local`);
              nodesToRemove.push(node.id);
            } else {
              console.error(`[reorganizeGraph] ❌ [${new Date().toISOString()}] Erreur lors de la mise à jour du nœud ${node.id}:`, error);
            }
          }
        }
      });

      console.log(`[reorganizeGraph] ⏳ [${new Date().toISOString()}] Attente de la fin des mises à jour...`);
      await Promise.all(updatePromises);
      console.log(`[reorganizeGraph] ✅ [${new Date().toISOString()}] Toutes les mises à jour terminées`);
      
      // Si des nœuds n'existent plus sur le backend, les retirer du store
      if (nodesToRemove.length > 0) {
        console.log(`[reorganizeGraph] 🗑️ [${new Date().toISOString()}] Suppression de ${nodesToRemove.length} nœuds inexistants...`);
        set((state) => ({
          nodes: state.nodes.filter(n => !nodesToRemove.includes(n.id)),
          edges: state.edges.filter(
            e => !nodesToRemove.includes(e.source) && !nodesToRemove.includes(e.target)
          ),
          selectedNode: nodesToRemove.includes(state.selectedNode?.id || '') 
            ? null 
            : state.selectedNode,
        }));
      }
      
      // Marquer la réorganisation comme terminée
      console.log(`[reorganizeGraph] ✅ [${new Date().toISOString()}] FIN - Réinitialisation de isSaving=false (temps total: ${Date.now() - startTime}ms)`);
      set({ isSaving: false });
    } catch (error) {
      console.error(`[reorganizeGraph] ❌ [${new Date().toISOString()}] ERREUR après ${Date.now() - startTime}ms:`, error);
      console.error(`[reorganizeGraph] Stack trace:`, error instanceof Error ? error.stack : 'N/A');
      const errorMessage = error instanceof ApiErrorResponse 
        ? error.detail 
        : 'Erreur lors de la réorganisation du graphe';
      set({ error: errorMessage, isSaving: false, isReorganizing: false });
    }
  },
  
  reset: () => set({
    mindmaps: [],
    currentMindmap: null,
    nodes: [],
    edges: [],
    selectedNode: null,
    error: null,
  }),
}));
