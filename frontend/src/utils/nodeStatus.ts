import type { NodeStatus } from '../../../shared/types';

/**
 * Mapping des statuts vers leurs couleurs
 * Ces couleurs sont utilisées pour représenter visuellement l'état des nœuds
 */
export const STATUS_COLORS: Record<NodeStatus, string> = {
  inbox: '#8B5CF6',    // Violet - nouveau/non traité
  clarify: '#FBBF24',  // Jaune - besoin de clarification
  ready: '#3B82F6',    // Bleu - prêt à être traité
  doing: '#10B981',    // Vert - en cours
  waiting: '#F59E0B',  // Orange - en attente
  done: '#6B7280',     // Gris - terminé
};

/**
 * Mapping des statuts vers leurs labels en français
 */
export const STATUS_LABELS: Record<NodeStatus, string> = {
  inbox: 'Boîte de réception',
  clarify: 'À clarifier',
  ready: 'Prêt',
  doing: 'En cours',
  waiting: 'En attente',
  done: 'Terminé',
};

/**
 * Liste ordonnée des statuts pour les sélecteurs
 */
export const STATUS_ORDER: NodeStatus[] = [
  'inbox',
  'clarify',
  'ready',
  'doing',
  'waiting',
  'done',
];

/**
 * Retourne la couleur associée à un statut
 * @param status - Le statut du nœud
 * @returns La couleur hexadécimale correspondante
 */
export function getStatusColor(status: NodeStatus | undefined): string {
  if (!status || !STATUS_COLORS[status]) {
    return '#00D9FF'; // Couleur par défaut (cyan)
  }
  return STATUS_COLORS[status];
}

/**
 * Retourne le label en français d'un statut
 * @param status - Le statut du nœud
 * @returns Le label en français
 */
export function getStatusLabel(status: NodeStatus | undefined): string {
  if (!status || !STATUS_LABELS[status]) {
    return 'Inconnu';
  }
  return STATUS_LABELS[status];
}

/**
 * Vérifie si une chaîne est un statut valide
 * @param value - La valeur à vérifier
 * @returns true si c'est un statut valide
 */
export function isValidStatus(value: string | undefined | null): value is NodeStatus {
  if (!value) return false;
  return STATUS_ORDER.includes(value as NodeStatus);
}
