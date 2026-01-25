/**
 * Layout ELK (Eclipse Layout Kernel) pour le mindmap
 * 
 * Utilise l'algorithme "layered" (basé sur Sugiyama) optimisé pour les arbres hiérarchiques.
 * Cet algorithme est utilisé dans de nombreux outils professionnels de visualisation de graphes.
 * 
 * Avantages:
 * - Espacement optimal entre les nœuds
 * - Évitement automatique des chevauchements
 * - Support des arbres avec plusieurs niveaux de profondeur
 * - Distribution équilibrée gauche/droite
 */

import ELK from 'elkjs/lib/elk.bundled.js';
import type { ElkNode, ElkExtendedEdge } from 'elkjs';
import type { Node, Edge } from '@xyflow/react';
import type { MindmapNodeData } from '../stores/mindmapStore';

// Instance ELK singleton
const elk = new ELK();

// Options de layout pour un mindmap horizontal (racine au centre, branches à gauche et droite)
const DEFAULT_LAYOUT_OPTIONS = {
  'elk.algorithm': 'layered',
  'elk.direction': 'RIGHT',
  'elk.layered.spacing.nodeNodeBetweenLayers': '80', // Espacement horizontal entre niveaux
  'elk.spacing.nodeNode': '40', // Espacement vertical entre nœuds du même niveau
  'elk.layered.spacing.edgeNodeBetweenLayers': '20',
  'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
  'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
  'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
  'elk.padding': '[top=20,left=20,bottom=20,right=20]',
};

// Options pour un layout "mrtree" (tree layout de Reingold-Tilford modifié)
const TREE_LAYOUT_OPTIONS = {
  'elk.algorithm': 'mrtree',
  'elk.spacing.nodeNode': '30', // Espacement entre nœuds frères
  'elk.mrtree.weighting': 'CONSTRAINT',
  'elk.mrtree.searchOrder': 'DFS',
};

// Options pour un layout radial (mindmap centré)
const RADIAL_LAYOUT_OPTIONS = {
  'elk.algorithm': 'radial',
  'elk.radial.compactor': 'WEDGE_COMPACTION',
  'elk.radial.optimizationCriteria': 'NONE',
};

export type LayoutType = 'layered' | 'tree' | 'radial';

/**
 * Calcule la position d'un handle sur un nœud
 */
function getHandlePosition(
  nodePosition: { x: number; y: number },
  handleId: 'source-left' | 'source-right' | 'target-left' | 'target-right',
  nodeWidth: number,
  nodeHeight: number
): { x: number; y: number } {
  const centerY = nodePosition.y + nodeHeight / 2;
  
  if (handleId === 'source-left' || handleId === 'target-left') {
    return { x: nodePosition.x, y: centerY };
  } else {
    return { x: nodePosition.x + nodeWidth, y: centerY };
  }
}

/**
 * Calcule la distance euclidienne entre deux points
 */
function getDistance(
  pos1: { x: number; y: number },
  pos2: { x: number; y: number }
): number {
  const dx = pos2.x - pos1.x;
  const dy = pos2.y - pos1.y;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Trouve les handles qui minimisent la distance entre deux nœuds
 * @param sourcePos Position du nœud source
 * @param targetPos Position du nœud target
 * @param nodeWidth Largeur des nœuds
 * @param nodeHeight Hauteur des nœuds
 * @returns Un objet avec sourceHandle et targetHandle qui minimisent la distance
 */
export function findOptimalHandles(
  sourcePos: { x: number; y: number },
  targetPos: { x: number; y: number },
  nodeWidth: number = 180,
  nodeHeight: number = 60
): { sourceHandle: 'source-left' | 'source-right'; targetHandle: 'target-left' | 'target-right' } {
  // Positions possibles pour les handles source
  const sourceLeftPos = getHandlePosition(sourcePos, 'source-left', nodeWidth, nodeHeight);
  const sourceRightPos = getHandlePosition(sourcePos, 'source-right', nodeWidth, nodeHeight);
  
  // Positions possibles pour les handles target
  const targetLeftPos = getHandlePosition(targetPos, 'target-left', nodeWidth, nodeHeight);
  const targetRightPos = getHandlePosition(targetPos, 'target-right', nodeWidth, nodeHeight);
  
  // Tester toutes les combinaisons possibles
  const combinations = [
    { sourceHandle: 'source-left' as const, targetHandle: 'target-left' as const, distance: getDistance(sourceLeftPos, targetLeftPos) },
    { sourceHandle: 'source-left' as const, targetHandle: 'target-right' as const, distance: getDistance(sourceLeftPos, targetRightPos) },
    { sourceHandle: 'source-right' as const, targetHandle: 'target-left' as const, distance: getDistance(sourceRightPos, targetLeftPos) },
    { sourceHandle: 'source-right' as const, targetHandle: 'target-right' as const, distance: getDistance(sourceRightPos, targetRightPos) },
  ];
  
  // Trouver la combinaison avec la distance minimale
  const optimal = combinations.reduce((min, current) => 
    current.distance < min.distance ? current : min
  );
  
  return {
    sourceHandle: optimal.sourceHandle,
    targetHandle: optimal.targetHandle,
  };
}

/**
 * Calcule le layout optimal pour un ensemble de nœuds et d'arêtes
 */
export async function calculateElkLayout(
  nodes: Node<MindmapNodeData>[],
  edges: Edge[],
  layoutType: LayoutType = 'layered',
  nodeWidth: number = 180,
  nodeHeight: number = 60
): Promise<{ nodes: Node<MindmapNodeData>[]; edges: Edge[] }> {
  if (nodes.length === 0) {
    return { nodes, edges };
  }

  // Créer un set des IDs des nœuds pour vérification rapide
  const nodeIds = new Set(nodes.map(n => n.id));
  
  // Filtrer les edges pour ne garder que ceux dont source et target existent
  const validEdges = edges.filter(
    (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)
  );
  
  if (validEdges.length < edges.length) {
    console.warn(`[ELK Layout] ${edges.length - validEdges.length} edge(s) ignoré(s) car référence(nt) des nœuds inexistants`);
  }

  // Sélectionner les options de layout
  let layoutOptions: Record<string, string>;
  switch (layoutType) {
    case 'tree':
      layoutOptions = TREE_LAYOUT_OPTIONS;
      break;
    case 'radial':
      layoutOptions = RADIAL_LAYOUT_OPTIONS;
      break;
    case 'layered':
    default:
      layoutOptions = DEFAULT_LAYOUT_OPTIONS;
  }

  // Construire le graphe ELK
  const elkGraph: ElkNode = {
    id: 'root',
    layoutOptions,
    children: nodes.map((node) => ({
      id: node.id,
      width: nodeWidth,
      height: nodeHeight,
    })),
    edges: validEdges.map((edge): ElkExtendedEdge => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target],
    })),
  };

  try {
    // Calculer le layout
    const layoutedGraph = await elk.layout(elkGraph);

    // Appliquer les nouvelles positions aux nœuds
    const layoutedNodes = nodes.map((node) => {
      const elkNode = layoutedGraph.children?.find((n) => n.id === node.id);
      if (elkNode && elkNode.x !== undefined && elkNode.y !== undefined) {
        return {
          ...node,
          position: {
            x: elkNode.x,
            y: elkNode.y,
          },
        };
      }
      return node;
    });

    return { nodes: layoutedNodes, edges: validEdges };
  } catch (error) {
    console.error('Erreur lors du calcul du layout ELK:', error);
    return { nodes, edges: validEdges };
  }
}

/**
 * Layout bidirectionnel pour mindmap (branches à gauche ET à droite du nœud racine)
 * Divise les enfants en deux groupes et applique un layout séparé pour chaque côté
 */
// Type pour les options ELK (ELK accepte string, number, boolean mais le type attend des strings)
type ElkLayoutOptions = Record<string, string>;

// Options ELK de base optimisées pour mindmap
const BASE_LAYERED_OPTIONS: ElkLayoutOptions = {
  'elk.algorithm': 'layered',
  'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
  'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
  'elk.layered.considerModelOrder.strategy': 'NODES_AND_EDGES', // Stabilité lors de l'ajout de nœuds
  'elk.layered.compaction.postCompaction.strategy': 'EDGE_LENGTH', // Compaction intelligente
  'elk.layered.spacing.nodeNodeBetweenLayers': '80',
  'elk.spacing.nodeNode': '60',
  'elk.layered.spacing.edgeNodeBetweenLayers': '20',
  'elk.padding': '[top=10,left=10,bottom=10,right=10]',
};

export async function calculateBidirectionalLayout(
  nodes: Node<MindmapNodeData>[],
  edges: Edge[],
  nodeWidth: number = 180,
  nodeHeight: number = 60
): Promise<{ nodes: Node<MindmapNodeData>[]; edges: Edge[] }> {
  if (nodes.length === 0) {
    return { nodes, edges };
  }

  // Trouver le nœud racine
  const rootNode = nodes.find((n) => n.data.isRoot);
  if (!rootNode) {
    // Pas de racine, utiliser le layout standard
    return calculateElkLayout(nodes, edges, 'layered', nodeWidth, nodeHeight);
  }

  // Trouver les enfants directs de la racine
  const rootBackendId = rootNode.data.backendId;
  const directChildren = nodes.filter(
    (n) => n.data.backendParentId === rootBackendId && !n.data.isRoot
  );

  // Si pas assez d'enfants pour diviser, utiliser le layout standard
  if (directChildren.length <= 1) {
    return calculateElkLayout(nodes, edges, 'layered', nodeWidth, nodeHeight);
  }

  // Fonction pour obtenir tous les descendants d'un nœud
  const getDescendants = (nodeId: string): string[] => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return [];
    
    const backendId = node.data.backendId;
    const children = nodes.filter((n) => n.data.backendParentId === backendId);
    
    let descendants: string[] = [];
    children.forEach((child) => {
      descendants.push(child.id);
      descendants = descendants.concat(getDescendants(child.id));
    });
    
    return descendants;
  };

  // Fonction pour calculer la taille du sous-arbre (poids)
  const subtreeSize = (nodeId: string): number => {
    return 1 + getDescendants(nodeId).length;
  };

  // Répartition équilibrée par poids de sous-arbre (au lieu de index % 2)
  // Trier les enfants par taille décroissante pour un meilleur équilibrage
  const sortedChildren = [...directChildren].sort((a, b) => subtreeSize(b.id) - subtreeSize(a.id));
  
  const leftChildren: string[] = [];
  const rightChildren: string[] = [];
  let leftWeight = 0;
  let rightWeight = 0;
  
  for (const child of sortedChildren) {
    const weight = subtreeSize(child.id);
    if (rightWeight <= leftWeight) {
      rightChildren.push(child.id);
      rightWeight += weight;
    } else {
      leftChildren.push(child.id);
      leftWeight += weight;
    }
  }
  
  console.log(`[calculateBidirectionalLayout] ⚖️ Répartition équilibrée - Left: ${leftWeight} poids (${leftChildren.length} enfants), Right: ${rightWeight} poids (${rightChildren.length} enfants)`);

  // Construire les sets complets pour chaque côté (INCLURE LA RACINE)
  const leftSet = new Set<string>([rootNode.id]); // ✅ Inclure la racine
  leftChildren.forEach((id) => {
    leftSet.add(id);
    getDescendants(id).forEach((d) => leftSet.add(d));
  });

  const rightSet = new Set<string>([rootNode.id]); // ✅ Inclure la racine
  rightChildren.forEach((id) => {
    rightSet.add(id);
    getDescendants(id).forEach((d) => rightSet.add(d));
  });

  // Note: nodeIds pourrait être utilisé pour vérification mais n'est pas nécessaire ici
  
  // Créer un set de tous les nœuds inclus dans leftSet ou rightSet
  const includedInLayout = new Set<string>();
  leftSet.forEach(id => includedInLayout.add(id));
  rightSet.forEach(id => includedInLayout.add(id));
  
  // Vérifier s'il y a des nœuds qui ne sont ni dans leftSet ni dans rightSet
  const orphanNodes = nodes.filter(n => !includedInLayout.has(n.id));
  if (orphanNodes.length > 0) {
    console.warn(`[calculateBidirectionalLayout] ⚠️ ${orphanNodes.length} nœuds orphelins détectés:`, 
      orphanNodes.map(n => ({ id: n.id, label: n.data.label, parentId: n.data.backendParentId }))
    );
    // Ajouter les nœuds orphelins au set droit par défaut
    orphanNodes.forEach(n => {
      rightSet.add(n.id);
      getDescendants(n.id).forEach(d => rightSet.add(d));
    });
    console.log(`[calculateBidirectionalLayout] 📍 ${orphanNodes.length} nœuds orphelins ajoutés au set droit`);
  }
  
  // Filtrer les nœuds pour chaque côté (incluant la racine)
  const leftNodes = nodes.filter((n) => leftSet.has(n.id));
  const rightNodes = nodes.filter((n) => rightSet.has(n.id));
  
  console.log(`[calculateBidirectionalLayout] 📊 Layout - Left: ${leftNodes.length} nœuds (dont racine), Right: ${rightNodes.length} nœuds (dont racine), Total: ${nodes.length}`);

  // Fonction pour construire un sous-graphe incluant la racine
  const buildSideGraph = (
    sideId: 'left' | 'right',
    sideSet: Set<string>,
    direction: 'LEFT' | 'RIGHT'
  ) => {
    const sideNodeIds = new Set(sideSet);
    const sideNodesList = nodes.filter(n => sideNodeIds.has(n.id));
    
    // Filtrer les edges : garder root→child du côté + edges internes au côté
    const sideEdgesList = edges.filter(e => {
      const inSide = sideNodeIds.has(e.source) && sideNodeIds.has(e.target);
      if (!inSide) return false;
      
      // ✅ Inclure les edges root→child ET les edges internes
      return true;
    });

    const layoutOptions: ElkLayoutOptions = {
      ...BASE_LAYERED_OPTIONS,
      'elk.direction': direction,
    };

    return {
      id: sideId,
      layoutOptions,
      children: sideNodesList.map(n => ({ id: n.id, width: nodeWidth, height: nodeHeight })),
      edges: sideEdgesList.map((e): ElkExtendedEdge => ({ id: e.id, sources: [e.source], targets: [e.target] })),
    };
  };

  // Construire les graphes gauche et droit (incluant la racine)
  const leftGraph = buildSideGraph('left', leftSet, 'LEFT');
  const rightGraph = buildSideGraph('right', rightSet, 'RIGHT');

  // Calculer les layouts séparément
  const [leftResult, rightResult] = await Promise.all([
    leftGraph.children.length > 0
      ? elk.layout(leftGraph)
      : null,
    rightGraph.children.length > 0
      ? elk.layout(rightGraph)
      : null,
  ]);

  // Position du nœud racine (centre)
  const rootX = 0;
  const rootY = 0;

  // Calculer les dimensions des layouts (utiliser les propriétés du layout ELK si disponibles)
  // ELK retourne un objet avec width et height, mais TypeScript ne le reconnaît pas toujours
  const leftHeight = leftResult && typeof leftResult === 'object' && 'height' in leftResult 
    ? (leftResult as { height?: number }).height || 0 
    : 0;
  const rightHeight = rightResult && typeof rightResult === 'object' && 'height' in rightResult 
    ? (rightResult as { height?: number }).height || 0 
    : 0;

  // Offset pour centrer verticalement
  const maxHeight = Math.max(leftHeight, rightHeight);
  const leftYOffset = (maxHeight - leftHeight) / 2;
  const rightYOffset = (maxHeight - rightHeight) / 2;

  // Construire le résultat final
  const layoutedNodes: Node<MindmapNodeData>[] = [];
  
  // ✅ Extraire la position de la racine depuis le layout ELK (left ou right, peu importe)
  // et l'ignorer pour placer la racine manuellement au centre
  let rootPositionFromLayout: { x: number; y: number } | null = null;
  if (leftResult?.children) {
    const rootInLeft = leftResult.children.find((n: any) => n.id === rootNode.id);
    if (rootInLeft && rootInLeft.x !== undefined && rootInLeft.y !== undefined) {
      rootPositionFromLayout = { x: rootInLeft.x, y: rootInLeft.y };
    }
  }
  if (!rootPositionFromLayout && rightResult?.children) {
    const rootInRight = rightResult.children.find((n: any) => n.id === rootNode.id);
    if (rootInRight && rootInRight.x !== undefined && rootInRight.y !== undefined) {
      rootPositionFromLayout = { x: rootInRight.x, y: rootInRight.y };
    }
  }

  // Ajouter le nœud racine au centre (position manuelle, ignorons celle d'ELK)
  layoutedNodes.push({
    ...rootNode,
    position: { x: rootX, y: rootY + maxHeight / 2 - nodeHeight / 2 },
  });

  // Ajouter les nœuds de gauche (décalés à gauche de la racine)
  // ✅ Ignorer la position de la racine dans le résultat ELK (on la place manuellement)
  if (leftResult?.children && leftResult.children.length > 0) {
    const nonRootChildren = leftResult.children.filter((n: any) => n.id !== rootNode.id);
    if (nonRootChildren.length > 0) {
      // Utiliser la position relative à la racine dans le layout ELK
      const rootXInLayout = rootPositionFromLayout?.x || 0;
      
      // Trouver le nœud le plus à droite (hors racine) pour calculer l'offset
      const rightmostNode = nonRootChildren.reduce((max: any, node: any) => 
        (node.x || 0) > (max.x || 0) ? node : max
      );
      const rightmostX = rightmostNode.x || 0;
      const rootToRightmostDistance = rightmostX - rootXInLayout;
      
      // Positionner le nœud le plus à droite à 80px à gauche du nœud racine
      const leftOffset = rootX - rootToRightmostDistance - nodeWidth - 80;
      
      nonRootChildren.forEach((elkNode: any) => {
        const originalNode = nodes.find((n) => n.id === elkNode.id);
        if (originalNode && elkNode.x !== undefined && elkNode.y !== undefined) {
          // Ajuster la position relative à la position de la racine dans le layout ELK
          const relativeX = elkNode.x - rootXInLayout;
          layoutedNodes.push({
            ...originalNode,
            position: {
              x: rootX + relativeX + leftOffset,
              y: leftYOffset + elkNode.y,
            },
          });
        }
      });
    }
  }

  // Ajouter les nœuds de droite (décalés à droite de la racine)
  // ✅ Ignorer la position de la racine dans le résultat ELK (on la place manuellement)
  if (rightResult?.children && rightResult.children.length > 0) {
    const nonRootChildren = rightResult.children.filter((n: any) => n.id !== rootNode.id);
    if (nonRootChildren.length > 0) {
      // Utiliser la position relative à la racine dans le layout ELK
      const rootXInLayout = rootPositionFromLayout?.x || 0;
      
      // Trouver le nœud le plus à gauche (hors racine) pour calculer l'offset
      const leftmostNode = nonRootChildren.reduce((min: any, node: any) => 
        (node.x || 0) < (min.x || 0) ? node : min
      );
      const leftmostX = leftmostNode.x || 0;
      const rootToLeftmostDistance = leftmostX - rootXInLayout;
      
      // Positionner le nœud le plus à gauche à 80px à droite du nœud racine
      const rightOffset = rootX - rootToLeftmostDistance + nodeWidth + 80;
      
      nonRootChildren.forEach((elkNode: any) => {
        const originalNode = nodes.find((n) => n.id === elkNode.id);
        if (originalNode && elkNode.x !== undefined && elkNode.y !== undefined) {
          // Ajuster la position relative à la position de la racine dans le layout ELK
          const relativeX = elkNode.x - rootXInLayout;
          layoutedNodes.push({
            ...originalNode,
            position: {
              x: rootX + relativeX + rightOffset,
              y: rightYOffset + elkNode.y,
            },
          });
        }
      });
    }
  }

  // Vérifier que tous les nœuds ont été inclus dans le layout
  const layoutedNodeIds = new Set(layoutedNodes.map(n => n.id));
  const missingNodes = nodes.filter(n => !layoutedNodeIds.has(n.id));
  
  if (missingNodes.length > 0) {
    console.warn(`[calculateBidirectionalLayout] ⚠️ ${missingNodes.length} nœuds non inclus dans le layout:`, 
      missingNodes.map(n => ({ id: n.id, label: n.data.label, parentId: n.data.backendParentId, isRoot: n.data.isRoot }))
    );
    
    // Ajouter les nœuds manquants (orphelins ou autres) avec leurs positions actuelles
    // ou une position par défaut si nécessaire
    missingNodes.forEach((node) => {
      // Si le nœud a un parent, le positionner relativement au parent
      if (node.data.backendParentId) {
        const parentInLayout = layoutedNodes.find(n => n.data.backendId === node.data.backendParentId);
        if (parentInLayout) {
          // Positionner relativement au parent (à droite par défaut)
          layoutedNodes.push({
            ...node,
            position: {
              x: parentInLayout.position.x + nodeWidth + 80,
              y: parentInLayout.position.y,
            },
          });
          console.log(`[calculateBidirectionalLayout] 📍 Nœud orphelin positionné relativement au parent: ${node.data.label}`);
        } else {
          // Parent pas trouvé, positionner à un endroit par défaut
          layoutedNodes.push({
            ...node,
            position: {
              x: rootX + 400,
              y: rootY + maxHeight / 2 + (missingNodes.indexOf(node) * (nodeHeight + 20)),
            },
          });
          console.log(`[calculateBidirectionalLayout] 📍 Nœud orphelin positionné par défaut: ${node.data.label}`);
        }
      } else {
        // Nœud racine ou orphelin sans parent, positionner à un endroit par défaut
        layoutedNodes.push({
          ...node,
          position: {
            x: rootX + 400,
            y: rootY + maxHeight / 2 + (missingNodes.indexOf(node) * (nodeHeight + 20)),
          },
        });
        console.log(`[calculateBidirectionalLayout] 📍 Nœud orphelin/racine supplémentaire positionné: ${node.data.label}`);
      }
    });
  }

  // Créer un map des positions finales pour calculer les handles
  const nodePositions = new Map<string, { x: number; y: number }>();
  layoutedNodes.forEach((n) => nodePositions.set(n.id, n.position));

  // Créer un set des IDs des nœuds dans le résultat (mis à jour avec les nœuds manquants)
  const finalLayoutedNodeIds = new Set(layoutedNodes.map(n => n.id));

  console.log(`[calculateBidirectionalLayout] ✅ Layout final - ${layoutedNodes.length} nœuds (dont ${missingNodes.length} ajoutés manuellement), ${edges.length} edges initiaux`);

  // Mettre à jour les edges avec les bons handles
  // Filtrer les edges invalides (source ou target manquant)
  const layoutedEdges: Edge[] = edges
    .filter((edge) => {
      // Vérifier que source et target existent dans les nœuds layoutés
      if (!finalLayoutedNodeIds.has(edge.source) || !finalLayoutedNodeIds.has(edge.target)) {
        console.warn(`[calculateBidirectionalLayout] Edge ${edge.id} ignoré: source ou target manquant (source: ${edge.source}, target: ${edge.target})`);
        return false;
      }
      return true;
    })
    .map((edge) => {
      const sourcePos = nodePositions.get(edge.source);
      const targetPos = nodePositions.get(edge.target);
      
      if (!sourcePos || !targetPos) {
        console.warn(`[calculateBidirectionalLayout] Edge ${edge.id}: position manquante pour source ou target`);
        return edge;
      }

      // Utiliser la fonction qui minimise la distance entre les nœuds
      const { sourceHandle, targetHandle } = findOptimalHandles(
        sourcePos,
        targetPos,
        nodeWidth,
        nodeHeight
      );
      
      return {
        ...edge,
        sourceHandle,
        targetHandle,
      };
    });

  console.log(`[calculateBidirectionalLayout] ✅ FIN - ${layoutedNodes.length} nœuds layoutés, ${layoutedEdges.length} edges valides`);

  return { nodes: layoutedNodes, edges: layoutedEdges };
}
