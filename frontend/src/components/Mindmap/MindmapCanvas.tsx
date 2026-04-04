import { useCallback, useMemo, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  BackgroundVariant,
  type NodeTypes,
  type EdgeTypes,
  type Node as ReactFlowNode,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Box, IconButton, Tooltip, Menu, MenuItem, ListItemIcon, ListItemText, Divider, Typography } from '@mui/material';
import { AutoAwesome as OrganizeIcon, Visibility as VisibilityIcon, VisibilityOff as VisibilityOffIcon } from '@mui/icons-material';
import MindmapNode from './MindmapNode';
import MindmapEdge from './MindmapEdge';
import { useMindmapStore, type MindmapNodeData } from '../../stores/mindmapStore';
import { mindmapsApi, triggersApi, type TriggerResponse } from '../../services/api';
import { STATUS_ORDER, getStatusColor, getStatusLabel } from '../../utils/nodeStatus';
import type { NodeStatus } from '../../../../shared/types';

const MindmapCanvas = () => {
  const mindmapStore = useMindmapStore();
  const currentMindmapId = useMindmapStore((s) => s.currentMindmap?.id);
  const { 
    nodes: storeNodes, 
    edges: storeEdges, 
    setNodes: setStoreNodes, 
    setEdges: setStoreEdges, 
    setSelectedNode,
    updateNode,
    selectedNode,
    reorganizeGraph,
    isSaving,
    updateEdgesHandles,
  } = mindmapStore;
  
  const updateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastSyncRevisionRef = useRef<number | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState(storeNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(storeEdges);
  const reactFlowInstance = useRef<any>(null);

  // État du menu contextuel pour le changement de statut
  const [contextMenu, setContextMenu] = useState<{
    mouseX: number;
    mouseY: number;
    nodeId: string;
    currentStatus: NodeStatus;
  } | null>(null);

  // État pour afficher/masquer les IDs
  const [showIds, setShowIds] = useState(false);

  const nodeTypes: NodeTypes = useMemo(
    () => ({
      mindmapNode: MindmapNode,
    }),
    []
  );

  const edgeTypes: EdgeTypes = useMemo(
    () => ({
      smoothstep: MindmapEdge,
      default: MindmapEdge,
    }),
    []
  );

  // Sync with store - only from store to canvas (one-way binding)
  // Utiliser des refs pour suivre les dernières valeurs sans créer de dépendance
  const localPositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const isDraggingRef = useRef<boolean>(false);
  const lastStoreNodeIdsRef = useRef<string>('');
  const lastStorePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const lastStoreDataRef = useRef<Map<string, string>>(new Map());
  
  useEffect(() => {
    // Ne pas synchroniser si on est en train de déplacer un nœud
    if (isDraggingRef.current) {
      return;
    }
    
    // Ne pas synchroniser pendant une mise à jour de nœud (mais permettre pendant la réorganisation)
    const { isUpdatingNode } = mindmapStore;
    if (isUpdatingNode) {
      return;
    }
    
    // Créer une chaîne d'IDs pour comparer avec la dernière valeur
    const storeNodeIds = storeNodes.map(n => n.id).sort().join(',');
    const nodesChanged = storeNodeIds !== lastStoreNodeIdsRef.current;
    
    // Comparer les positions et les données pour détecter les changements réels
    let positionsChanged = false;
    let dataChanged = false;
    
    if (!nodesChanged) {
      // Si même IDs, vérifier les positions et les données
      for (const storeNode of storeNodes) {
        const lastPosition = lastStorePositionsRef.current.get(storeNode.id);
        if (!lastPosition || 
            Math.abs(lastPosition.x - storeNode.position.x) > 1 ||
            Math.abs(lastPosition.y - storeNode.position.y) > 1) {
          positionsChanged = true;
          break;
        }
        
        // Vérifier si les données ont changé en comparant avec les dernières données stockées
        const storeDataStr = JSON.stringify({
          label: storeNode.data.label,
          description: storeNode.data.description,
          color: storeNode.data.color,
          status: storeNode.data.status,
          isRoot: storeNode.data.isRoot,
        });
        const lastDataStr = lastStoreDataRef.current.get(storeNode.id);
        if (lastDataStr !== storeDataStr) {
          dataChanged = true;
          break;
        }
      }
    }
    
    // Ne mettre à jour que si quelque chose a vraiment changé
    if (!nodesChanged && !positionsChanged && !dataChanged) {
      return;
    }
    
    // Mettre à jour les refs avec les nouvelles valeurs
    lastStoreNodeIdsRef.current = storeNodeIds;
    lastStorePositionsRef.current = new Map(
      storeNodes.map(n => [n.id, { x: n.position.x, y: n.position.y }])
    );
    lastStoreDataRef.current = new Map(
      storeNodes.map(n => [n.id, JSON.stringify({
        label: n.data.label,
        description: n.data.description,
        color: n.data.color,
        status: n.data.status,
        isRoot: n.data.isRoot,
      })])
    );
    
    // Fusionner les nœuds : utiliser les positions locales si elles existent (drag en cours)
    const mergedNodes = storeNodes.map(storeNode => {
      const localPosition = localPositionsRef.current.get(storeNode.id);
      // Si une position locale existe (drag en cours), l'utiliser
      // Sinon utiliser la position du store
      const position = localPosition || storeNode.position;
      
      return {
        ...storeNode,
        position,
        data: { ...storeNode.data, showIds }
      };
    });
    
    setNodes(mergedNodes);
    
    // Si des nœuds ont été ajoutés ou supprimés, réorganiser la vue
    if (nodesChanged && storeNodes.length > 0 && reactFlowInstance.current) {
      setTimeout(() => {
        reactFlowInstance.current.fitView({ padding: 0.5, duration: 400 });
      }, 200);
    }
  }, [storeNodes, setNodes, showIds]);

  useEffect(() => {
    const storeEdgeIds = storeEdges.map(e => e.id).sort().join(',');
    
    console.log('Syncing edges from store to canvas:', {
      storeCount: storeEdges.length,
      storeIds: storeEdgeIds
    });
    
    // Toujours mettre à jour avec de nouvelles références d'objets
    // Ajouter les IDs backend et la prop showIds aux edges
    const newEdges = storeEdges.map(edge => {
      const sourceNode = storeNodes.find(n => n.id === edge.source);
      const targetNode = storeNodes.find(n => n.id === edge.target);
      
      const edgeData = {
        sourceBackendId: sourceNode?.data.backendId,
        targetBackendId: targetNode?.data.backendId,
        showIds,
      };
      
      return {
        ...edge,
        data: edgeData,
      };
    });
    setEdges(newEdges);
  }, [storeEdges, setEdges, storeNodes, showIds]);

  const onConnect = useCallback(
    async (connection: Connection) => {
      if (!connection.source || !connection.target) {
        return;
      }

      // Trouver les nœuds source et target
      const sourceNode = mindmapStore.nodes.find((n) => n.id === connection.source);
      const targetNode = mindmapStore.nodes.find((n) => n.id === connection.target);

      if (!sourceNode || !targetNode) {
        console.error('[MindmapCanvas] Nœud source ou target introuvable');
        return;
      }

      if (!sourceNode.data.backendId || !targetNode.data.backendId) {
        console.error('[MindmapCanvas] backendId manquant pour source ou target');
        return;
      }

      // Ne pas permettre de relier un nœud à lui-même
      if (sourceNode.id === targetNode.id) {
        console.warn('[MindmapCanvas] Impossible de relier un nœud à lui-même');
        return;
      }

      // Ne pas permettre de créer un lien si source est déjà enfant de target
      if (sourceNode.data.backendParentId === targetNode.data.backendId) {
        console.info('[MindmapCanvas] Le nœud source est déjà enfant de ce parent');
        return;
      }

      // Vérifier qu'on ne crée pas un cycle
      // Avec la nouvelle logique (source devient enfant de target),
      // un cycle serait créé si target est un descendant de source
      // (car alors source → target → ... → source)
      const isDescendant = (nodeId: string, ancestorId: string, visited: Set<string> = new Set()): boolean => {
        // Protection contre les cycles : si on a déjà visité ce nœud, arrêter
        if (visited.has(nodeId)) {
          console.warn(`[MindmapCanvas] Cycle détecté lors de la vérification: ${nodeId}`);
          return false;
        }
        
        // Limiter la profondeur pour éviter une récursion trop profonde
        if (visited.size > 50) {
          console.warn(`[MindmapCanvas] Profondeur maximale atteinte lors de la vérification`);
          return false;
        }
        
        const node = mindmapStore.nodes.find(n => n.id === nodeId);
        if (!node) return false;
        
        // Si le nœud n'a pas de parent, ce n'est pas un descendant
        if (node.data.backendParentId === undefined || node.data.backendParentId === null) return false;
        
        const parentId = `node-${node.data.backendParentId}`;
        
        // Si le parent est l'ancêtre recherché, c'est un descendant
        if (parentId === ancestorId) return true;
        
        // Ajouter ce nœud aux visités et continuer la recherche
        visited.add(nodeId);
        return isDescendant(parentId, ancestorId, visited);
      };

      // Vérification de cycle : bloquer si targetNode est un descendant de sourceNode
      // Car avec la nouvelle logique (source devient enfant de target),
      // on aurait : source → target → ... → source (cycle)
      // 
      // Exemple avec structure A → B → C :
      // - Si on trace C → A (source=C, target=A) : A n'est pas descendant de C → valide (C devient enfant de A)
      // - Si on trace A → C (source=A, target=C) : C est descendant de A → BLOQUÉ (créerait A → C → ... → A)
      if (isDescendant(targetNode.id, sourceNode.id)) {
        console.warn(`[MindmapCanvas] Impossible de créer un lien circulaire: ${targetNode.data.label} est un descendant de ${sourceNode.data.label} (créerait un cycle)`);
        return;
      }

      // Nouvelle logique : quand on trace un lien de A vers B,
      // le nœud SOURCE (A) devient enfant du nœud TARGET (B)
      // C'est la sémantique intuitive : "je déplace A vers B" signifie "A devient enfant de B"
      try {
        // Mettre à jour le parent du nœud SOURCE dans le backend
        // Le nœud source (d'où on part) devient enfant du nœud target (où on arrive)
        await mindmapStore.updateNode(sourceNode.id, {
          backendParentId: targetNode.data.backendId,
        });

        // Recharger les nœuds depuis le backend pour obtenir l'état à jour
        // (edges recréés proprement par loadNodes)
        const currentMindmap = mindmapStore.currentMindmap;
        if (currentMindmap) {
          await mindmapStore.loadNodes(currentMindmap.id);
          
          // Ajuster la vue après le rechargement
          if (reactFlowInstance.current) {
            setTimeout(() => {
              reactFlowInstance.current.fitView({ padding: 0.5, duration: 400 });
            }, 400);
          }
        }
      } catch (error) {
        console.error('[MindmapCanvas] Erreur lors de la mise à jour du parent:', error);
      }
    },
    [mindmapStore]
  );

  // Rafraîchir le graphe si un trigger cron (ou autre job) a modifié le mindmap en arrière-plan
  useEffect(() => {
    if (currentMindmapId == null) {
      lastSyncRevisionRef.current = null;
      return;
    }
    lastSyncRevisionRef.current = null;

    let cancelled = false;
    const poll = async () => {
      try {
        const { revision } = await mindmapsApi.getSyncRevision(currentMindmapId);
        if (cancelled) return;
        const prev = lastSyncRevisionRef.current;
        lastSyncRevisionRef.current = revision;
        if (prev !== null && revision > prev) {
          await useMindmapStore.getState().loadNodes(currentMindmapId);
        }
      } catch (e) {
        console.error('[MindmapCanvas] sync-revision:', e);
      }
    };

    void poll();
    const intervalId = window.setInterval(poll, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [currentMindmapId]);

  // Charger les triggers quand un nœud est sélectionné
  // Note: On utilise une ref pour éviter la boucle infinie causée par nodes dans les dépendances
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;
  
  useEffect(() => {
    const loadTriggers = async () => {
      if (!selectedNode?.data.backendId) return;
      
      try {
        const triggers = await triggersApi.listByNode(selectedNode.data.backendId);
        const currentNodes = nodesRef.current;
        const updatedNodes = currentNodes.map((n) => {
          if (n.id === selectedNode.id) {
            return {
              ...n,
              data: {
                ...n.data,
                triggers,
              },
            };
          }
          return n;
        });
        setNodes(updatedNodes);
        setStoreNodes(updatedNodes);
      } catch (error) {
        console.error('Erreur lors du chargement des triggers:', error);
      }
    };

    loadTriggers();
  }, [selectedNode?.id, selectedNode?.data.backendId, setNodes, setStoreNodes]);

  // Réorganiser la vue au chargement initial
  useEffect(() => {
    if (nodes.length > 0 && reactFlowInstance.current) {
      setTimeout(() => {
        reactFlowInstance.current.fitView({ padding: 0.5, duration: 400 });
      }, 300);
    }
  }, []); // Seulement au montage du composant
  
  // Sauvegarder automatiquement les changements de position avec debounce
  useEffect(() => {
    return () => {
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }
    };
  }, []);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: typeof nodes[0]) => {
      setSelectedNode(node);
    },
    [setSelectedNode]
  );

  // Gérer les changements de nœuds (positions, etc.)
  const handleNodesChange = useCallback(
    (changes: any[]) => {
      // Mettre à jour les nœuds locaux avec React Flow
      onNodesChange(changes);
      
      // Traiter les changements de position
      const positionChanges = changes.filter(
        (change) => change.type === 'position' && change.position
      );
      
      // Mettre à jour la ref des positions locales pour le drag en cours
      if (positionChanges.length > 0) {
        const isDragging = positionChanges.some((change) => change.dragging);
        isDraggingRef.current = isDragging;
        
        positionChanges.forEach((change) => {
          if (change.position) {
            localPositionsRef.current.set(change.id, change.position);
          }
        });
        
        // Mettre à jour le store avec les nouvelles positions seulement si le drag est terminé
        const finishedDrags = positionChanges.filter((change) => !change.dragging);
        
        if (finishedDrags.length > 0) {
          // Le drag est terminé, mettre à jour le store
          isDraggingRef.current = false;
          
          const currentState = mindmapStore.nodes;
          const updatedNodes = currentState.map((node) => {
            const change = finishedDrags.find((c) => c.id === node.id);
            if (change && change.position) {
              return {
                ...node,
                position: change.position,
              };
            }
            return node;
          });
          
          setStoreNodes(updatedNodes);
          
          // Recalculer les handles des edges pour minimiser la distance
          updateEdgesHandles();
          
          // Débouncer les mises à jour de position sur le backend
          if (updateTimeoutRef.current) {
            clearTimeout(updateTimeoutRef.current);
          }
          
          updateTimeoutRef.current = setTimeout(() => {
            finishedDrags.forEach((change) => {
              // Nettoyer la ref après la sauvegarde
              localPositionsRef.current.delete(change.id);
              
              const state = mindmapStore.nodes;
              const node = state.find((n) => n.id === change.id);
              if (node?.data.backendId) {
                // Sauvegarder la position sur le backend
                updateNode(change.id, {});
              }
            });
          }, 1000); // Attendre 1 seconde après le dernier changement
        }
      }
    },
    [onNodesChange, setStoreNodes, updateNode, mindmapStore, updateEdgesHandles]
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setContextMenu(null);
  }, [setSelectedNode]);

  // Gestionnaire du clic droit sur un nœud pour afficher le menu contextuel
  const onNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: ReactFlowNode<MindmapNodeData>) => {
      // Empêcher le menu contextuel par défaut du navigateur
      event.preventDefault();
      
      const currentStatus = node.data.status || 'inbox';
      
      setContextMenu({
        mouseX: event.clientX,
        mouseY: event.clientY,
        nodeId: node.id,
        currentStatus,
      });
    },
    []
  );

  // Fermer le menu contextuel
  const handleCloseContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  // Changer le statut d'un nœud via le menu contextuel
  const handleStatusChange = useCallback(
    async (newStatus: NodeStatus) => {
      if (!contextMenu) return;

      try {
        await updateNode(contextMenu.nodeId, { status: newStatus });
        handleCloseContextMenu();
      } catch (error) {
        console.error('[MindmapCanvas] Erreur lors du changement de statut:', error);
      }
    },
    [contextMenu, updateNode, handleCloseContextMenu]
  );

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        '& .react-flow__background': {
          backgroundColor: 'transparent',
        },
        '& .react-flow__controls': {
          background: 'rgba(18, 24, 43, 0.9)',
          border: '1px solid rgba(0, 217, 255, 0.2)',
          borderRadius: '12px',
          overflow: 'hidden',
          '& button': {
            background: 'transparent',
            borderBottom: '1px solid rgba(0, 217, 255, 0.1)',
            color: '#E8EDF5',
            '&:hover': {
              background: 'rgba(0, 217, 255, 0.1)',
            },
            '& svg': {
              fill: '#E8EDF5',
            },
          },
        },
        '& .react-flow__minimap': {
          background: 'rgba(18, 24, 43, 0.9)',
          border: '1px solid rgba(0, 217, 255, 0.2)',
          borderRadius: '12px',
          overflow: 'hidden',
        },
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onNodeContextMenu={onNodeContextMenu}
        onPaneClick={onPaneClick}
        onInit={(instance) => {
          reactFlowInstance.current = instance;
        }}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.5 }}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: false,
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="rgba(0, 217, 255, 0.15)"
        />
        <Controls position="bottom-left" style={{ bottom: 16, left: 16 }} />
        <MiniMap
          position="bottom-right"
          style={{ bottom: 16, right: 16 }}
          nodeColor={(node) => {
            const data = node.data as MindmapNodeData;
            return getStatusColor(data.status);
          }}
          maskColor="rgba(10, 14, 23, 0.8)"
        />
        
        {/* Boutons de contrôle */}
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            gap: 1,
          }}
        >
          <Tooltip title="Réorganiser le graphe" placement="bottom">
            <span>
              <IconButton
                onClick={async () => {
                  await reorganizeGraph();
                  if (reactFlowInstance.current) {
                    setTimeout(() => {
                      reactFlowInstance.current.fitView({ padding: 0.5, duration: 400 });
                    }, 200);
                  }
                }}
                disabled={isSaving || storeNodes.length === 0}
                sx={{
                  backgroundColor: 'rgba(18, 24, 43, 0.9)',
                  border: '1px solid rgba(0, 217, 255, 0.2)',
                  color: '#00D9FF',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 217, 255, 0.1)',
                  },
                  '&:disabled': {
                    color: 'rgba(0, 217, 255, 0.3)',
                  },
                }}
              >
                <OrganizeIcon />
              </IconButton>
            </span>
          </Tooltip>
          
          <Tooltip title={showIds ? "Masquer les IDs" : "Afficher les IDs"} placement="bottom">
            <span>
              <IconButton
                onClick={() => setShowIds(!showIds)}
                sx={{
                  backgroundColor: 'rgba(18, 24, 43, 0.9)',
                  border: '1px solid rgba(0, 217, 255, 0.2)',
                  color: showIds ? '#00D9FF' : 'rgba(0, 217, 255, 0.5)',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 217, 255, 0.1)',
                  },
                }}
              >
                {showIds ? <VisibilityIcon /> : <VisibilityOffIcon />}
              </IconButton>
            </span>
          </Tooltip>
        </Box>
      </ReactFlow>

      {/* Menu contextuel pour changer le statut */}
      <Menu
        open={contextMenu !== null}
        onClose={handleCloseContextMenu}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu !== null
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
        slotProps={{
          paper: {
            sx: {
              backgroundColor: 'rgba(18, 24, 43, 0.98)',
              border: '1px solid rgba(0, 217, 255, 0.2)',
              borderRadius: '12px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
              minWidth: 200,
            },
          },
        }}
      >
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Changer le statut
          </Typography>
        </Box>
        <Divider sx={{ borderColor: 'rgba(0, 217, 255, 0.1)' }} />
        {STATUS_ORDER.map((status) => (
          <MenuItem
            key={status}
            onClick={() => handleStatusChange(status)}
            selected={contextMenu?.currentStatus === status}
            sx={{
              py: 1.5,
              '&:hover': {
                backgroundColor: `${getStatusColor(status)}20`,
              },
              '&.Mui-selected': {
                backgroundColor: `${getStatusColor(status)}30`,
                '&:hover': {
                  backgroundColor: `${getStatusColor(status)}40`,
                },
              },
            }}
          >
            <ListItemIcon>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  backgroundColor: getStatusColor(status),
                  boxShadow: `0 0 8px ${getStatusColor(status)}80`,
                }}
              />
            </ListItemIcon>
            <ListItemText
              primary={getStatusLabel(status)}
              primaryTypographyProps={{
                fontSize: '0.9rem',
                fontWeight: contextMenu?.currentStatus === status ? 600 : 400,
              }}
            />
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
};

export default MindmapCanvas;
