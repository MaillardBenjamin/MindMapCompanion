import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Box,
  Typography,
  TextField,
  Button,
  IconButton,
  Chip,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  RadioGroup,
  Radio,
  FormLabel,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Close as CloseIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Schedule as ScheduleIcon,
  Webhook as WebhookIcon,
  Rule as ConditionIcon,
  TouchApp as ManualIcon,
  Save as SaveIcon,
  AddCircle as AddCircleIcon,
  PlayArrow as PlayIcon,
  ScreenLockPortrait as ScreenIcon,
  Email as EmailIcon,
  NoteAdd as NoteAddIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { useMindmapStore } from '../../stores/mindmapStore';
import { useNotification } from '../../hooks/useNotification';
import { 
  triggersApi, 
  configurableAgentsApi, 
  actionsApi,
  nodesApi,
  ApiErrorResponse,
  type TriggerCreate,
  type ConfigurableAgentResponse,
  type ActionResponse,
  type TriggerManualExecuteRequest,
  type TriggerManualExecuteResponse,
} from '../../services/api';
import TriggerForm from '../Trigger/TriggerForm';
import { STATUS_ORDER, getStatusColor, getStatusLabel } from '../../utils/nodeStatus';
import type { NodeStatus } from '../../../../shared/types';

// Mapping des anciens types vers les nouveaux types
const oldToNewTriggerType: Record<string, string> = {
  'schedule': 'cron',
  'webhook': 'email_received',
  'condition': 'state_changed',
  'manual': 'manual',
};

// Mapping inverse pour l'affichage
const newToOldTriggerType: Record<string, string> = {
  'cron': 'schedule',
  'email_received': 'webhook',
  'state_changed': 'condition',
  'date_reached': 'schedule',
  'manual': 'manual',
};

// Fonction helper pour obtenir le type d'affichage
const getDisplayType = (triggerType: string): string => {
  return newToOldTriggerType[triggerType] || triggerType;
};

const triggerIcons: Record<string, JSX.Element> = {
  schedule: <ScheduleIcon fontSize="small" />,
  webhook: <WebhookIcon fontSize="small" />,
  condition: <ConditionIcon fontSize="small" />,
  manual: <ManualIcon fontSize="small" />,
  cron: <ScheduleIcon fontSize="small" />,
  email_received: <WebhookIcon fontSize="small" />,
  state_changed: <ConditionIcon fontSize="small" />,
  date_reached: <ScheduleIcon fontSize="small" />,
};

const triggerLabels: Record<string, string> = {
  schedule: 'Planifié',
  webhook: 'Webhook',
  condition: 'Condition',
  manual: 'Manuel',
  cron: 'Planifié',
  email_received: 'Email reçu',
  state_changed: 'Changement d\'état',
  date_reached: 'Date atteinte',
};

const triggerColors: Record<string, string> = {
  schedule: '#FBBF24',
  webhook: '#4ADE80',
  condition: '#8B5CF6',
  manual: '#FF6B9D',
  cron: '#FBBF24',
  email_received: '#4ADE80',
  state_changed: '#8B5CF6',
  date_reached: '#FBBF24',
};

const CRON_DAY_LABELS = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];

/** Parse une expression cron simple (minute heure * * jours) en champs locaux — aligné sur TriggerForm. */
function parseCronExpressionToLocalFields(expr: string): { hour: number; minute: number; days: number[] } | null {
  const cronParts = expr.trim().split(/\s+/);
  if (cronParts.length < 5) return null;
  const utcMinute = parseInt(cronParts[0], 10) || 0;
  const utcHour = parseInt(cronParts[1], 10) || 0;
  const daysPart = cronParts[4];
  const today = new Date();
  const utcDate = new Date(
    Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate(), utcHour, utcMinute),
  );
  const localHour = utcDate.getHours();
  const localMinute = utcDate.getMinutes();
  const days: number[] = [];
  if (daysPart === '*') {
    for (let i = 0; i <= 6; i += 1) days.push(i);
  } else if (daysPart) {
    daysPart.split(',').forEach((range) => {
      if (range.includes('-')) {
        const [start, end] = range.split('-').map(Number);
        for (let i = start; i <= end; i += 1) {
          if (i >= 0 && i <= 6) days.push(i);
        }
      } else {
        const day = parseInt(range, 10);
        if (day >= 0 && day <= 6) days.push(day);
      }
    });
  }
  return { hour: localHour, minute: localMinute, days };
}

/** Résumé heure + jours pour l’affichage carte trigger planifié (config TriggerForm). */
function formatCronScheduleSummary(config: unknown): { timeLine: string; daysLine: string | null } | null {
  if (!config || typeof config !== 'object') return null;
  const c = config as Record<string, unknown>;
  let hour = c.cron_hour;
  let minute = c.cron_minute;
  let days: number[] = Array.isArray(c.cron_days)
    ? (c.cron_days as unknown[]).map((x) => Number(x)).filter((n) => !Number.isNaN(n))
    : [];
  const expr = typeof c.cron_expression === 'string' ? c.cron_expression : '';

  if (expr && (hour === undefined || minute === undefined || days.length === 0)) {
    const parsed = parseCronExpressionToLocalFields(expr);
    if (parsed) {
      if (hour === undefined) hour = parsed.hour;
      if (minute === undefined) minute = parsed.minute;
      if (days.length === 0) days = parsed.days;
    }
  }

  if (hour !== undefined && minute !== undefined) {
    const timeLine = `Heure : ${String(Number(hour)).padStart(2, '0')}:${String(Number(minute)).padStart(2, '0')}`;
    let daysLine: string | null;
    if (days.length === 0) {
      daysLine = 'Jours : —';
    } else if (days.length === 7) {
      daysLine = 'Jours : tous les jours';
    } else {
      const labels = [...new Set(days)]
        .sort((a, b) => a - b)
        .map((d) => CRON_DAY_LABELS[d] ?? `J${d}`);
      daysLine = `Jours : ${labels.join(', ')}`;
    }
    return { timeLine, daysLine };
  }

  if (expr.trim()) {
    return { timeLine: `Expression : ${expr}`, daysLine: null };
  }
  return null;
}

function isCronLikeTrigger(triggerType: string): boolean {
  return triggerType === 'cron' || triggerType === 'schedule';
}

const IMPORTANCE_FR: Record<string, string> = {
  high: 'élevée',
  medium: 'moyenne',
  low: 'faible',
};
const DIRECTION_FR: Record<string, string> = {
  emerging: 'émergente',
  growing: 'en croissance',
  declining: 'en déclin',
  stable: 'stable',
};
const PRIORITY_FR: Record<string, string> = {
  urgent: 'urgente',
  high: 'élevée',
  medium: 'moyenne',
  low: 'faible',
};
const RELIABILITY_FR: Record<string, string> = {
  high: 'élevée',
  medium: 'moyenne',
  low: 'faible',
};
const TYPE_FR: Record<string, string> = {
  news: 'actualité',
  blog: 'blog',
  social: 'réseau social',
  official: 'officiel',
  research: 'recherche',
  other: 'autre',
};

function shouldRenderNewsMonitorMarkdown(parsed: Record<string, unknown>): boolean {
  const es = parsed.executive_summary;
  if (typeof es === 'string' && es.trim()) return true;
  const kf = parsed.key_findings;
  if (Array.isArray(kf) && kf.length > 0) return true;
  const tr = parsed.trends;
  if (Array.isArray(tr) && tr.length > 0) return true;
  const src = parsed.sources;
  if (Array.isArray(src) && src.length > 0) return true;
  const rec = parsed.recommendations;
  if (Array.isArray(rec) && rec.length > 0) return true;
  const ns = parsed.next_steps;
  if (typeof ns === 'string' && ns.trim()) return true;
  const rd = parsed.report_date ?? parsed.rapport_date;
  if (typeof rd === 'string' && rd.trim()) return true;
  return false;
}

function indentBody(text: string, prefix: string): string {
  return text.replace(/\n/g, `\n${prefix}`);
}

/** Rendu markdown FR pour la sortie structurée type News Monitor (aligné sur le backend). */
function newsMonitorParsedToMarkdown(parsed: Record<string, unknown>): string {
  const parts: string[] = [];

  const theme = parsed.theme;
  if (typeof theme === 'string' && theme.trim()) {
    parts.push(`## ${theme.trim()}\n\n`);
  }

  const es = parsed.executive_summary;
  if (typeof es === 'string' && es.trim()) {
    parts.push('### Résumé exécutif\n\n', es.trim(), '\n\n');
  }

  const kf = parsed.key_findings;
  if (Array.isArray(kf) && kf.length > 0) {
    parts.push('### Points clés\n\n');
    for (const item of kf) {
      if (!item || typeof item !== 'object') continue;
      const it = item as Record<string, unknown>;
      const title = typeof it.title === 'string' ? it.title.trim() : '';
      const bodyRaw = it.description ?? it.summary;
      const body = typeof bodyRaw === 'string' ? bodyRaw.trim() : '';
      if (title) parts.push(`- **${title}**`);
      else if (body) parts.push('- *(Sans titre)*');
      if (body) parts.push(`\n\n  ${indentBody(body, '  ')}\n`);
      else if (title) parts.push('\n');
      const meta: string[] = [];
      if (typeof it.importance === 'string' && it.importance.trim()) {
        const im = it.importance.trim();
        meta.push(`Importance : ${IMPORTANCE_FR[im] ?? im}`);
      }
      if (typeof it.source === 'string' && it.source.trim()) {
        meta.push(`Source : ${it.source.trim()}`);
      }
      if (typeof it.date === 'string' && it.date.trim()) {
        meta.push(`Date : ${it.date.trim()}`);
      }
      if (meta.length) parts.push(`  \n  *${meta.join(' · ')}*\n`);
      parts.push('\n');
    }
  }

  const trends = parsed.trends;
  if (Array.isArray(trends) && trends.length > 0) {
    parts.push('### Tendances\n\n');
    for (const item of trends) {
      if (!item || typeof item !== 'object') continue;
      const it = item as Record<string, unknown>;
      const name = typeof it.trend_name === 'string' ? it.trend_name.trim() : '';
      const desc = typeof it.description === 'string' ? it.description.trim() : '';
      if (name) parts.push(`- **${name}**`);
      else if (desc) parts.push('- *(Sans titre)*');
      if (desc) parts.push(`\n\n  ${indentBody(desc, '  ')}\n`);
      else if (name) parts.push('\n');
      const meta: string[] = [];
      if (typeof it.direction === 'string' && it.direction.trim()) {
        const d = it.direction.trim();
        meta.push(`Direction : ${DIRECTION_FR[d] ?? d}`);
      }
      if (typeof it.impact === 'string' && it.impact.trim()) {
        meta.push(`Impact : ${it.impact.trim()}`);
      }
      if (meta.length) parts.push(`  \n  *${meta.join(' · ')}*\n`);
      parts.push('\n');
    }
  }

  const sources = parsed.sources;
  if (Array.isArray(sources) && sources.length > 0) {
    parts.push('### Sources\n\n');
    for (const item of sources) {
      if (!item || typeof item !== 'object') continue;
      const it = item as Record<string, unknown>;
      const name = typeof it.name === 'string' ? it.name.trim() : '';
      const url = typeof it.url === 'string' ? it.url.trim() : '';
      const extras: string[] = [];
      if (typeof it.type === 'string' && it.type.trim()) {
        const t = it.type.trim();
        extras.push(TYPE_FR[t] ?? t);
      }
      if (typeof it.reliability === 'string' && it.reliability.trim()) {
        const r = it.reliability.trim();
        extras.push(`fiabilité : ${RELIABILITY_FR[r] ?? r}`);
      }
      let line = name ? `- **${name}**` : '- *(sans nom)*';
      if (extras.length) line += ` — ${extras.join(', ')}`;
      parts.push(`${line}\n`);
      if (url) parts.push(`  - ${url}\n`);
    }
    parts.push('\n');
  }

  const recs = parsed.recommendations;
  if (Array.isArray(recs) && recs.length > 0) {
    parts.push('### Recommandations\n\n');
    for (const item of recs) {
      if (!item || typeof item !== 'object') continue;
      const it = item as Record<string, unknown>;
      const action = typeof it.action === 'string' ? it.action.trim() : '';
      const rationale = typeof it.rationale === 'string' ? it.rationale.trim() : '';
      let priFr = '';
      if (typeof it.priority === 'string' && it.priority.trim()) {
        const p = it.priority.trim();
        priFr = ` *(priorité : ${PRIORITY_FR[p] ?? p})*`;
      }
      if (action) parts.push(`- **${action}**${priFr}\n`);
      if (rationale) {
        parts.push(`  - ${indentBody(rationale, '  - ')}\n`);
      }
      parts.push('\n');
    }
  }

  const ns = parsed.next_steps;
  if (typeof ns === 'string' && ns.trim()) {
    parts.push('### Prochaines étapes\n\n', ns.trim(), '\n\n');
  }

  const rd = parsed.report_date ?? parsed.rapport_date;
  if (typeof rd === 'string' && rd.trim()) {
    parts.push(`*Date du rapport : ${rd.trim()}*\n`);
  }

  return parts.join('').trim();
}

/** Extrait le texte markdown à persister depuis la sortie d'exécution d'agent (News Monitor, etc.). */
function extractMarkdownFromExecuteOutput(output: {
  output_raw?: string;
  output_parsed?: Record<string, unknown> | null;
} | null | undefined): string | null {
  if (!output) return null;
  const raw = (output.output_raw || '').trim();
  const parsed = output.output_parsed;
  if (parsed && typeof parsed === 'object') {
    const md = parsed.markdown;
    if (typeof md === 'string' && md.trim()) return md.trim();
    if (shouldRenderNewsMonitorMarkdown(parsed)) {
      const built = newsMonitorParsedToMarkdown(parsed);
      if (built.trim()) return built.trim();
    }
  }
  if (raw) return raw;
  if (parsed && typeof parsed === 'object') {
    try {
      return '```json\n' + JSON.stringify(parsed, null, 2) + '\n```';
    } catch {
      return null;
    }
  }
  return null;
}

/** Markdown affiché dans la zone « Réponse de l'agent » (FR structuré si disponible). */
function getAgentResponseMarkdownForDisplay(output: {
  output_raw?: string;
  output_parsed?: Record<string, unknown> | null;
} | null | undefined): string {
  if (!output) return '';
  return extractMarkdownFromExecuteOutput(output) ?? (output.output_raw || '').trim();
}

/** Libellé par défaut pour un nœud « résultats » : date ISO + titre du nœud parent. */
function buildDefaultResultChildLabel(parentLabel: string): string {
  const iso = new Date().toISOString().slice(0, 10);
  const t = (parentLabel || 'Sans titre').trim() || 'Sans titre';
  return `${iso} — ${t}`.slice(0, 200);
}

const OUTPUT_TYPES = ['screen', 'email', 'audio_tts', 'audio_email', 'mindmap_child'] as const;
type OutputRenderType = (typeof OUTPUT_TYPES)[number];

const parseInputSchemaFromMarkdown = (markdown?: string) => {
  if (!markdown) return null;
  try {
    const sectionMatch = markdown.match(/#\s*Input Schema[\s\S]*?(?=^#\s|\Z)/m);
    if (!sectionMatch) return null; // Pas de section Input Schema → ne pas utiliser le premier bloc JSON (évite de prendre l'Output Schema)
    const sectionContent = sectionMatch[0];
    const jsonMatch =
      sectionContent.match(/```json\s*([\s\S]*?)```/m) ||
      sectionContent.match(/```\s*([\s\S]*?)```/m);
    if (!jsonMatch) return null;
    return JSON.parse(jsonMatch[1]);
  } catch {
    return null;
  }
};

const NodeDetails = () => {
  const { selectedNode, setSelectedNode, updateNode, addTrigger, removeTrigger, deleteNode, addChildNode, isSaving, currentMindmap, loadNodes } = useMindmapStore();
  const { showSuccess, showError, showWarning } = useNotification();
  const [editLabel, setEditLabel] = useState(selectedNode?.data.label || '');
  const [editDescription, setEditDescription] = useState(selectedNode?.data.description || '');
  const [editStatus, setEditStatus] = useState<NodeStatus>(selectedNode?.data.status || 'inbox');
  const [showAddTrigger, setShowAddTrigger] = useState(false);
  const [showAddChildNode, setShowAddChildNode] = useState(false);
  const [newChildNodeLabel, setNewChildNodeLabel] = useState('');
  const [editingTrigger, setEditingTrigger] = useState<any>(null);
  const [triggerFormOpen, setTriggerFormOpen] = useState(false);
  
  // États pour le lancement manuel de trigger
  const [showManualExecute, setShowManualExecute] = useState(false);
  const [selectedTriggerForExecute, setSelectedTriggerForExecute] = useState<any>(null);
  const [taskType, setTaskType] = useState<'agent' | 'action'>('agent');
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [selectedAction, setSelectedAction] = useState<string>('');
  const [outputType, setOutputType] = useState<OutputRenderType>('screen');
  const [inputText, setInputText] = useState('');
  const [emailTo, setEmailTo] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [availableAgents, setAvailableAgents] = useState<ConfigurableAgentResponse[]>([]);
  const [availableActions, setAvailableActions] = useState<ActionResponse[]>([]);
  const [agentOptions, setAgentOptions] = useState<Record<string, any>>({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState<any>(null);
  const [executeError, setExecuteError] = useState<string>('');
  const [streamingText, setStreamingText] = useState('');
  const [streamingStatus, setStreamingStatus] = useState('');
  const [resultChildLabel, setResultChildLabel] = useState('');
  const [savingResultChild, setSavingResultChild] = useState(false);
  const [descriptionMdDialogOpen, setDescriptionMdDialogOpen] = useState(false);
  const [streamingToolResults, setStreamingToolResults] = useState<Array<{ toolName: string; resultPreview: string }>>([]);
  const streamContainerRef = useRef<HTMLDivElement>(null);

  // Synchroniser editLabel, editDescription et editStatus avec selectedNode quand il change
  useEffect(() => {
    if (selectedNode) {
      setEditLabel(selectedNode.data.label || '');
      setEditDescription(selectedNode.data.description || '');
      setEditStatus(selectedNode.data.status || 'inbox');
      setDescriptionMdDialogOpen(false);
    }
  }, [selectedNode?.id, selectedNode?.data.label, selectedNode?.data.description, selectedNode?.data.status]);

  // Scroll automatique vers le bas pendant le stream (trigger manuel)
  useEffect(() => {
    if (streamContainerRef.current && isExecuting) {
      streamContainerRef.current.scrollTop = streamContainerRef.current.scrollHeight;
    }
  }, [streamingText, streamingStatus, streamingToolResults, isExecuting]);

  // Ne pas rendre AnimatePresence si aucun nœud n'est sélectionné
  if (!selectedNode) {
    return null;
  }

  const handleSave = async () => {
    console.log('Saving node:', selectedNode.id, { label: editLabel, description: editDescription, status: editStatus });
    try {
      await updateNode(selectedNode.id, {
        label: editLabel,
        description: editDescription,
        status: editStatus,
      });
      showSuccess("Nœud mis à jour avec succès");
    } catch (error) {
      console.error("Erreur lors de la sauvegarde:", error);
      showError("Erreur lors de la mise à jour du nœud");
    }
  };


  const handleDelete = async () => {
    if (!selectedNode) return;
    const nodeIdToDelete = selectedNode.id;
    console.log('Deleting node:', nodeIdToDelete);
    
    // Désélectionner le nœud avant la suppression pour fermer le panneau
    setSelectedNode(null);
    
    // Attendre un peu pour que le panneau se ferme
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Supprimer le nœud
    try {
      await deleteNode(nodeIdToDelete);
      showSuccess("Nœud supprimé avec succès");
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
      showError("Erreur lors de la suppression du nœud");
    }
  };

  const handleAddChildNodeClick = () => {
    console.log(`[NodeDetails] 🖱️ [${new Date().toISOString()}] handleAddChildNodeClick - selectedNode: ${selectedNode?.id}, label: ${selectedNode?.data.label}`);
    setNewChildNodeLabel('');
    setShowAddChildNode(true);
    console.log(`[NodeDetails] ✅ [${new Date().toISOString()}] Dialogue ouvert pour ajout de sous-nœud`);
  };

  const handleAddChildNodeConfirm = async () => {
    const startTime = Date.now();
    console.log(`[NodeDetails] 🖱️ [${new Date().toISOString()}] handleAddChildNodeConfirm DÉBUT`);
    console.log(`[NodeDetails] État - selectedNode: ${selectedNode?.id}, label input: "${newChildNodeLabel}", isSaving: ${isSaving}`);
    
    if (!selectedNode) {
      console.error(`[NodeDetails] ❌ [${new Date().toISOString()}] Aucun nœud sélectionné`);
      return;
    }
    
    const label = newChildNodeLabel.trim() || `Sous-nœud de ${selectedNode.data.label}`;
    console.log(`[NodeDetails] 📝 [${new Date().toISOString()}] Label final: "${label}"`);
    console.log(`[NodeDetails] 🔄 [${new Date().toISOString()}] Appel de addChildNode(${selectedNode.id}, "${label}")...`);
    
    try {
      await addChildNode(selectedNode.id, label);
      console.log(`[NodeDetails] ✅ [${new Date().toISOString()}] addChildNode terminé (temps: ${Date.now() - startTime}ms)`);
      showSuccess("Sous-nœud créé avec succès");
    } catch (error) {
      console.error(`[NodeDetails] ❌ [${new Date().toISOString()}] Erreur dans addChildNode:`, error);
      console.error(`[NodeDetails] Stack trace:`, error instanceof Error ? error.stack : 'N/A');
      showError("Erreur lors de la création du sous-nœud");
    }
    
    console.log(`[NodeDetails] 🔄 [${new Date().toISOString()}] Fermeture du dialogue...`);
    setShowAddChildNode(false);
    setNewChildNodeLabel('');
    console.log(`[NodeDetails] ✅ [${new Date().toISOString()}] handleAddChildNodeConfirm FIN (temps total: ${Date.now() - startTime}ms)`);
  };

  const handleAddChildNodeCancel = () => {
    setShowAddChildNode(false);
    setNewChildNodeLabel('');
  };

  // Charger les agents configurables et actions quand le dialogue s'ouvre
  useEffect(() => {
    if (showManualExecute) {
      loadAvailableAgents();
      loadAvailableActions();
    }
  }, [showManualExecute, selectedNode]);

  const loadAvailableAgents = async () => {
    try {
      const response = await configurableAgentsApi.list();
      setAvailableAgents(response.agents || []);
    } catch (error) {
      console.error('Erreur lors du chargement des agents:', error);
    }
  };

  const loadAvailableActions = async () => {
    if (!selectedNode?.data.triggers || selectedNode.data.triggers.length === 0) {
      setAvailableActions([]);
      return;
    }

    try {
      // Charger les actions du premier trigger (ou tous les triggers)
      const allActions: ActionResponse[] = [];
      for (const trigger of selectedNode.data.triggers) {
        if (typeof trigger.id === 'number') {
          const actions = await actionsApi.listByTrigger(trigger.id);
          allActions.push(...actions);
        }
      }
      setAvailableActions(allActions);
    } catch (error) {
      console.error('Erreur lors du chargement des actions:', error);
    }
  };

  const handleOpenManualExecute = (trigger: any) => {
    console.log('[NodeDetails] handleOpenManualExecute appelé pour trigger:', trigger);
    console.log('[NodeDetails] Trigger ID:', trigger?.id, 'Type:', typeof trigger?.id);
    console.log('[NodeDetails] Configuration du trigger:', trigger?.config);
    
    if (!trigger || !trigger.id) {
      console.error('[NodeDetails] Trigger invalide - pas d\'ID:', trigger);
      return;
    }
    
    // S'assurer que le formulaire de configuration est fermé
    setTriggerFormOpen(false);
    setEditingTrigger(null);
    // Ouvrir le dialogue d'exécution manuelle
    setSelectedTriggerForExecute(trigger);
    setShowManualExecute(true);
    
    // Charger la configuration du trigger si elle existe
    const config = trigger.config || {};
    console.log('[NodeDetails] Configuration chargée:', config);
    
    // Pré-remplir avec la configuration sauvegardée ou valeurs par défaut
    // La config peut avoir selected_agent/selected_action ou task_id
    const taskType = config.task_type || 'agent';
    const taskId = config.task_id || (taskType === 'agent' ? config.selected_agent : config.selected_action);
    
    setTaskType(taskType);
    setSelectedAgent(taskType === 'agent' ? String(taskId || '') : '');
    setSelectedAction(taskType === 'action' ? String(taskId || '') : '');
    const rawOt = config.output_type as string | undefined;
    setOutputType(
      rawOt && OUTPUT_TYPES.includes(rawOt as OutputRenderType)
        ? (rawOt as OutputRenderType)
        : 'screen',
    );
    setInputText(config.input_text || '');
    setAgentOptions(config.agent_options || {});
    // La config peut avoir email_config ou email_to/email_subject directement
    setEmailTo(config.email_config?.to || config.email_to || '');
    setEmailSubject(config.email_config?.subject || config.email_subject || '');
    setExecuteResult(null);
    setExecuteError('');
    setResultChildLabel(buildDefaultResultChildLabel(selectedNode?.data.label || ''));
  };

  const handleCloseManualExecute = () => {
    setShowManualExecute(false);
    setSelectedTriggerForExecute(null);
    setExecuteResult(null);
    setExecuteError('');
    setStreamingText('');
    setStreamingStatus('');
    setStreamingToolResults([]);
    setResultChildLabel('');
    setSavingResultChild(false);
    setDescriptionMdDialogOpen(false);
  };

  const handleCreateResultChildNode = async () => {
    if (!selectedNode?.data.backendId || !currentMindmap) {
      showError('Sélectionnez un mindmap et un nœud parent.');
      return;
    }
    const md = extractMarkdownFromExecuteOutput(executeResult?.output);
    if (!md) {
      showError('Aucun contenu à enregistrer.');
      return;
    }
    const label =
      resultChildLabel.trim() || buildDefaultResultChildLabel(selectedNode.data.label || '');
    setSavingResultChild(true);
    try {
      const px = Math.round(selectedNode.position.x + 200);
      const py = Math.round(selectedNode.position.y);
      const created = await nodesApi.create({
        mindmap_id: currentMindmap.id,
        parent_id: selectedNode.data.backendId,
        label: label.slice(0, 200),
        description: md,
        color: selectedNode.data.color || '#00D9FF',
        position_x: px,
        position_y: py,
        is_root: false,
        status: 'inbox',
      });
      await loadNodes(currentMindmap.id);
      const newFlow = useMindmapStore.getState().nodes.find((n) => n.data.backendId === created.id);
      if (newFlow) {
        setSelectedNode(newFlow);
      }
      showSuccess('Nœud enfant créé avec le rendu.');
      handleCloseManualExecute();
    } catch (error: unknown) {
      console.error(error);
      const detail = error instanceof ApiErrorResponse ? error.detail : 'Erreur lors de la création du nœud';
      showError(detail);
    } finally {
      setSavingResultChild(false);
    }
  };

  const handleExecuteTrigger = async () => {
    if (!selectedTriggerForExecute || !selectedTriggerForExecute.id) {
      setExecuteError('Trigger invalide');
      return;
    }

    // Convertir l'ID en string si nécessaire (peut être un nombre ou une string)
    const triggerId = String(selectedTriggerForExecute.id);

    const taskId = taskType === 'agent' ? selectedAgent : selectedAction;
    if (!taskId) {
      setExecuteError(`Veuillez sélectionner un ${taskType === 'agent' ? 'agent' : 'action'}`);
      return;
    }

    if ((outputType === 'email' || outputType === 'audio_email') && !emailTo) {
      setExecuteError('Veuillez saisir une adresse email');
      return;
    }

    setIsExecuting(true);
    setExecuteError('');
    setExecuteResult(null);
    setStreamingText('');
    setStreamingStatus('');
    setStreamingToolResults([]);

    const effectiveInputText = taskType === 'agent' && agentOptions.input_text != null && agentOptions.input_text !== ''
      ? String(agentOptions.input_text)
      : (inputText || undefined);
    const request: TriggerManualExecuteRequest = {
      trigger_id: triggerId,
      task_type: taskType,
      task_id: taskId,
      output_type: outputType,
      input_text: effectiveInputText,
      agent_options: taskType === 'agent' && Object.keys(agentOptions).length > 0 ? agentOptions : undefined,
      email_config: (outputType === 'email' || outputType === 'audio_email') ? {
        to: emailTo,
        subject: emailSubject || undefined,
      } : undefined,
    };

    const useStream = taskType === 'agent' && outputType === 'screen';
    const agentName = taskType === 'agent' ? availableAgents.find(a => String(a.id) === selectedAgent)?.name : undefined;

    try {
      console.log('[NodeDetails] 🚀 Démarrage de l\'exécution du trigger:', {
        triggerId,
        taskType,
        taskId,
        outputType,
        useStream,
      });

      if (useStream) {
        let streamedBuffer = '';
        await triggersApi.executeStream(triggerId, request, {
          onChunk: (content) => {
            streamedBuffer += content;
            setStreamingText((prev) => prev + content);
          },
          onStatus: (message) => setStreamingStatus((prev) => (prev ? `${prev}\n${message}` : message)),
          onToolResult: (toolName, resultPreview) =>
            setStreamingToolResults((prev) => [...prev, { toolName, resultPreview }]),
          onDone: (final) => {
            const finalOutput = (final.output_raw && final.output_raw.trim().length > 0)
              ? final.output_raw
              : streamedBuffer;
            setExecuteResult({
              success: true,
              message: 'Exécution terminée',
              output: {
                output_raw: finalOutput,
                output_parsed: final.output_parsed ?? undefined,
                execution_time_ms: final.execution_time_ms,
                agent_name: agentName,
                input_text: effectiveInputText,
              },
            });
            setStreamingText('');
            setStreamingStatus('');
            setStreamingToolResults([]);
          },
          onError: (message) => setExecuteError(message),
        });
      } else {
        const result = await triggersApi.execute(triggerId, request);
        console.log('[NodeDetails] ✅ Résultat de l\'exécution:', result);
        if (result.output) {
          console.group('📊 Détails de l\'exécution');
          if (result.output.execution_time_ms) {
            console.log(`⏱️  Temps d'exécution: ${result.output.execution_time_ms}ms`);
          }
          console.groupEnd();
        }
        setExecuteResult(result);
        if (
          result.success &&
          outputType === 'mindmap_child' &&
          result.output?.child_node_id &&
          currentMindmap
        ) {
          await loadNodes(currentMindmap.id);
          const nf = useMindmapStore.getState().nodes.find(
            (n) => n.data.backendId === result.output.child_node_id,
          );
          if (nf) {
            setSelectedNode(nf);
          }
        }
      }
    } catch (error: any) {
      const errorMessage = error.detail || error.message || 'Erreur lors de l\'exécution';
      console.error('[NodeDetails] ❌ Erreur lors de l\'exécution:', error);
      setExecuteError(errorMessage);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <>
    <AnimatePresence mode="wait">
      {selectedNode && (
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 50 }}
          transition={{ duration: 0.3 }}
          style={{
            position: 'absolute',
            top: 16,
            right: 16,
            bottom: 16,
            width: 340,
            zIndex: 10,
          }}
        >
        <Box
          sx={{
            height: '100%',
            backgroundColor: '#12182B',
            backdropFilter: 'blur(20px)',
            borderRadius: '16px',
            border: '1px solid rgba(0, 217, 255, 0.2)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <Box
            sx={{
              px: 2.5,
              py: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid rgba(0, 217, 255, 0.1)',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: selectedNode.data.color || '#00D9FF',
                  boxShadow: `0 0 10px ${selectedNode.data.color || '#00D9FF'}`,
                }}
              />
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                Détails du nœud
              </Typography>
            </Box>
            <IconButton
              size="small"
              onClick={() => setSelectedNode(null)}
              sx={{ color: 'text.secondary' }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>

          {/* Content */}
          <Box sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', p: 2.5 }}>
            {/* Edit Fields */}
            <TextField
              fullWidth
              label="Titre"
              value={editLabel}
              onChange={(e) => setEditLabel(e.target.value)}
              size="small"
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              label="Description"
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              multiline
              rows={3}
              size="small"
              sx={{ mb: 1 }}
            />
            {editDescription.trim().length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Button
                  size="small"
                  variant="text"
                  onClick={() => setDescriptionMdDialogOpen(true)}
                  sx={{ textTransform: 'none', color: '#00D9FF' }}
                >
                  Afficher le descriptif
                </Button>
              </Box>
            )}

            {/* Sélecteur de statut */}
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel>Statut</InputLabel>
              <Select
                value={editStatus}
                label="Statut"
                onChange={(e) => setEditStatus(e.target.value as NodeStatus)}
                sx={{
                  '& .MuiSelect-select': {
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                  },
                }}
              >
                {STATUS_ORDER.map((status) => (
                  <MenuItem
                    key={status}
                    value={status}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
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
                    <Box
                      sx={{
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        backgroundColor: getStatusColor(status),
                        boxShadow: `0 0 6px ${getStatusColor(status)}80`,
                        flexShrink: 0,
                      }}
                    />
                    {getStatusLabel(status)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button
              variant="contained"
              fullWidth
              startIcon={<SaveIcon />}
              onClick={handleSave}
              disabled={isSaving}
              sx={{ mb: 2 }}
            >
              {isSaving ? 'Sauvegarde...' : 'Sauvegarder'}
            </Button>

            <Button
              variant="outlined"
              fullWidth
              startIcon={<AddCircleIcon />}
              onClick={handleAddChildNodeClick}
              disabled={isSaving}
              sx={{ mb: 3 }}
            >
              Ajouter un sous-nœud
            </Button>

            <Divider sx={{ my: 2 }} />

            {/* Triggers Section */}
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Triggers & Actions
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => setShowAddTrigger(!showAddTrigger)}
                  sx={{
                    color: 'primary.main',
                    background: 'rgba(0, 217, 255, 0.1)',
                    '&:hover': { background: 'rgba(0, 217, 255, 0.2)' },
                  }}
                >
                  <AddIcon fontSize="small" />
                </IconButton>
              </Box>

              {/* Add Trigger Form */}
              <AnimatePresence>
                {showAddTrigger && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <Box
                      sx={{
                        p: 2,
                        mb: 2,
                        borderRadius: '12px',
                        background: 'rgba(0, 217, 255, 0.05)',
                        border: '1px solid rgba(0, 217, 255, 0.1)',
                      }}
                    >
                      <Button
                        variant="contained"
                        fullWidth
                        size="small"
                        onClick={() => {
                          // Ouvrir directement le formulaire de configuration sans créer de trigger
                          setShowAddTrigger(false);
                          setEditingTrigger(null);
                          setTriggerFormOpen(true);
                        }}
                        disabled={isSaving}
                      >
                        {isSaving ? 'Ajout...' : 'Créer un trigger'}
                      </Button>
                    </Box>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Triggers List */}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                {selectedNode.data.triggers?.map((trigger) => (
                  <Box
                    key={trigger.id}
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      background: `${triggerColors[trigger.trigger_type] || triggerColors[getDisplayType(trigger.trigger_type)]}10`,
                      border: `1px solid ${triggerColors[trigger.trigger_type] || triggerColors[getDisplayType(trigger.trigger_type)]}30`,
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Box sx={{ color: triggerColors[trigger.trigger_type] || triggerColors[getDisplayType(trigger.trigger_type)] }}>
                          {triggerIcons[trigger.trigger_type] || triggerIcons[getDisplayType(trigger.trigger_type)]}
                        </Box>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {triggerLabels[trigger.trigger_type] || triggerLabels[getDisplayType(trigger.trigger_type)] || trigger.trigger_type}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={async () => {
                          if (typeof trigger.id === 'number' && selectedNode) {
                            console.log('[NodeDetails] Suppression du trigger:', trigger.id);
                            try {
                              const removeFromStore = async () => {
                                console.log('[NodeDetails] Trigger supprimé, mise à jour du store...');
                                
                                // Mettre à jour le store manuellement pour forcer le re-render
                                const store = useMindmapStore.getState();
                                const updatedNodes = store.nodes.map((node) => {
                                  if (node.id === selectedNode.id) {
                                    return {
                                      ...node,
                                      data: {
                                        ...node.data,
                                        triggers: (node.data.triggers || []).filter((t) => t.id !== trigger.id),
                                      },
                                    };
                                  }
                                  return node;
                                });
                                
                                // Mettre à jour le store et forcer la mise à jour du selectedNode
                                useMindmapStore.setState({ nodes: updatedNodes });
                                const updatedSelectedNode = updatedNodes.find(n => n.id === selectedNode.id);
                                if (updatedSelectedNode) {
                                  setSelectedNode(updatedSelectedNode);
                                }
                                
                                // Recharger depuis le serveur si on a un mindmap
                                if (currentMindmap) {
                                  console.log('[NodeDetails] Rechargement du mindmap...');
                                  await loadNodes(currentMindmap.id);
                                }
                                
                                console.log('[NodeDetails] Suppression terminée');
                              };

                              // Supprimer via l'API
                              await triggersApi.delete(trigger.id);
                              await removeFromStore();
                            } catch (error) {
                              if (error instanceof ApiErrorResponse && error.status === 404) {
                                console.warn('[NodeDetails] Trigger déjà supprimé côté serveur, nettoyage du store...');
                                await (async () => {
                                  const store = useMindmapStore.getState();
                                  const updatedNodes = store.nodes.map((node) => {
                                    if (node.id === selectedNode.id) {
                                      return {
                                        ...node,
                                        data: {
                                          ...node.data,
                                          triggers: (node.data.triggers || []).filter((t) => t.id !== trigger.id),
                                        },
                                      };
                                    }
                                    return node;
                                  });
                                  useMindmapStore.setState({ nodes: updatedNodes });
                                  const updatedSelectedNode = updatedNodes.find(n => n.id === selectedNode.id);
                                  if (updatedSelectedNode) {
                                    setSelectedNode(updatedSelectedNode);
                                  }
                                  if (currentMindmap) {
                                    console.log('[NodeDetails] Rechargement du mindmap...');
                                    await loadNodes(currentMindmap.id);
                                  }
                                  console.log('[NodeDetails] Suppression terminée');
                                })();
                                return;
                              }
                              console.error('[NodeDetails] Erreur lors de la suppression:', error);
                              alert('Erreur lors de la suppression du trigger');
                            }
                          }
                        }}
                        disabled={typeof trigger.id !== 'number' || isSaving}
                        sx={{ color: 'error.main' }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                    {isCronLikeTrigger(trigger.trigger_type) &&
                      (() => {
                        const sched = formatCronScheduleSummary(trigger.config);
                        if (!sched) return null;
                        return (
                          <Box sx={{ mb: 1, pl: 4.25, pr: 0.5 }}>
                            <Typography
                              variant="caption"
                              sx={{ color: 'text.secondary', display: 'block', lineHeight: 1.45 }}
                            >
                              {sched.timeLine}
                            </Typography>
                            {sched.daysLine && (
                              <Typography
                                variant="caption"
                                sx={{
                                  color: 'text.secondary',
                                  display: 'block',
                                  lineHeight: 1.45,
                                  mt: 0.25,
                                }}
                              >
                                {sched.daysLine}
                              </Typography>
                            )}
                          </Box>
                        );
                      })()}
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 1 }}>
                      <Chip
                        label={triggerLabels[trigger.trigger_type] || triggerLabels[getDisplayType(trigger.trigger_type)] || trigger.trigger_type}
                        size="small"
                        sx={{
                          background: `${triggerColors[trigger.trigger_type] || triggerColors[getDisplayType(trigger.trigger_type)]}20`,
                          color: triggerColors[trigger.trigger_type] || triggerColors[getDisplayType(trigger.trigger_type)],
                          fontSize: '0.7rem',
                        }}
                      />
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<PlayIcon />}
                          onClick={() => {
                            console.log('[NodeDetails] Clic sur Lancer pour trigger:', trigger);
                            handleOpenManualExecute(trigger);
                          }}
                          disabled={!trigger.enabled || isSaving}
                          sx={{
                            fontSize: '0.7rem',
                            px: 1,
                            py: 0.5,
                          }}
                        >
                          Lancer
                        </Button>
                        <IconButton
                          size="small"
                          onClick={() => {
                            console.log('[NodeDetails] Clic sur Éditer pour trigger:', trigger);
                            // Convertir le format du trigger pour TriggerForm
                            const triggerForForm = {
                              id: String(trigger.id),
                              trigger_type: trigger.trigger_type,
                              config: trigger.config || {},
                              enabled: trigger.enabled,
                            };
                            setEditingTrigger(triggerForForm);
                            setTriggerFormOpen(true);
                            // S'assurer que le dialogue d'exécution est fermé
                            setShowManualExecute(false);
                          }}
                          sx={{ color: 'primary.main' }}
                          title="Configurer le trigger"
                        >
                          <SaveIcon fontSize="small" />
                        </IconButton>
                        <FormControlLabel
                          control={
                            <Switch
                              size="small"
                              checked={trigger.enabled}
                              sx={{
                                '& .MuiSwitch-switchBase.Mui-checked': {
                                  color: triggerColors[trigger.trigger_type] || triggerColors[getDisplayType(trigger.trigger_type)],
                                },
                                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                                  backgroundColor: triggerColors[trigger.trigger_type] || triggerColors[getDisplayType(trigger.trigger_type)],
                                },
                              }}
                            />
                          }
                          label=""
                        />
                      </Box>
                    </Box>
                  </Box>
                ))}

                {(!selectedNode.data.triggers || selectedNode.data.triggers.length === 0) && (
                  <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
                    Aucun trigger configuré
                  </Typography>
                )}
              </Box>
            </Box>
          </Box>

          {/* Footer */}
          {!selectedNode.data.isRoot && (
            <Box
              sx={{
                p: 2,
                borderTop: '1px solid rgba(0, 217, 255, 0.1)',
              }}
            >
              <Button
                variant="outlined"
                fullWidth
                color="error"
                startIcon={<DeleteIcon />}
                onClick={handleDelete}
              >
                Supprimer le nœud
              </Button>
            </Box>
          )}
        </Box>
      </motion.div>
      )}
    </AnimatePresence>

    {/* Dialogue pour nommer le sous-nœud */}
    <Dialog
      open={showAddChildNode}
      onClose={handleAddChildNodeCancel}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 1,
          pr: 1,
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0, pt: 0.25 }}>Ajouter un sous-nœud</Box>
        <IconButton
          aria-label="Fermer la fenêtre"
          onClick={handleAddChildNodeCancel}
          edge="end"
          size="small"
          disabled={isSaving}
          sx={{ color: 'text.secondary', flexShrink: 0, mt: -0.25 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          margin="dense"
          label="Nom du sous-nœud"
          fullWidth
          variant="outlined"
          value={newChildNodeLabel}
          onChange={(e) => setNewChildNodeLabel(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleAddChildNodeConfirm();
            }
          }}
          placeholder={selectedNode ? `Sous-nœud de ${selectedNode.data.label}` : ''}
          sx={{ mt: 2 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleAddChildNodeCancel}>Annuler</Button>
        <Button onClick={handleAddChildNodeConfirm} variant="contained" disabled={isSaving}>
          Ajouter
        </Button>
      </DialogActions>
    </Dialog>

    {/* Dialogue pour lancer un trigger manuellement */}
    <Dialog
      open={showManualExecute}
      onClose={handleCloseManualExecute}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 1,
          pr: 1,
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0, pt: 0.25 }}>
          Lancer le trigger manuellement
          {selectedTriggerForExecute && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {triggerLabels[selectedTriggerForExecute.trigger_type] || triggerLabels[getDisplayType(selectedTriggerForExecute.trigger_type)] || selectedTriggerForExecute.trigger_type}
            </Typography>
          )}
        </Box>
        <IconButton
          aria-label="Fermer la fenêtre"
          onClick={handleCloseManualExecute}
          disabled={isExecuting}
          edge="end"
          size="small"
          sx={{ color: 'text.secondary', flexShrink: 0, mt: -0.25 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          {/* Type de task */}
          <FormControl fullWidth>
            <FormLabel>Type de task</FormLabel>
            <RadioGroup
              row
              value={taskType}
              onChange={(e) => {
                setTaskType(e.target.value as 'agent' | 'action');
                setSelectedAgent('');
                setSelectedAction('');
                setAgentOptions({});
              }}
            >
              <FormControlLabel value="agent" control={<Radio />} label="Agent" />
              <FormControlLabel value="action" control={<Radio />} label="Action" />
            </RadioGroup>
          </FormControl>

          {/* Sélection de l'agent ou action */}
          <FormControl fullWidth>
            <InputLabel>
              {taskType === 'agent' ? 'Sélectionner un agent' : 'Sélectionner une action'}
            </InputLabel>
            <Select
              value={taskType === 'agent' ? selectedAgent : selectedAction}
              label={taskType === 'agent' ? 'Sélectionner un agent' : 'Sélectionner une action'}
              onChange={(e) => {
                if (taskType === 'agent') {
                  setSelectedAgent(e.target.value);
                  setAgentOptions({});
                } else {
                  setSelectedAction(e.target.value);
                }
              }}
            >
              {taskType === 'agent' ? (
                availableAgents.map((agent) => (
                  <MenuItem key={agent.id} value={String(agent.id)}>
                    <Box>
                      <Typography variant="body2" fontWeight={500}>
                        {agent.name}
                      </Typography>
                      {agent.description && (
                        <Typography variant="caption" color="text.secondary">
                          {agent.description}
                        </Typography>
                      )}
                    </Box>
                  </MenuItem>
                ))
              ) : (
                availableActions.map((action) => (
                  <MenuItem key={action.id} value={String(action.id)}>
                    <Box>
                      <Typography variant="body2" fontWeight={500}>
                        {action.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {action.action_type}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>

          {/* Champs dynamiques de l'agent ou texte d'entrée générique */}
          {taskType === 'agent' && selectedAgent && (() => {
            const selectedAgentData = availableAgents.find(a => String(a.id) === selectedAgent);
            const resolvedInputSchema =
              selectedAgentData?.input_schema ||
              parseInputSchemaFromMarkdown(selectedAgentData?.markdown_config);
            const hasInputSchema = resolvedInputSchema && Object.keys(resolvedInputSchema).length > 0;

            if (hasInputSchema) {
              return (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Paramètres de l'agent
                  </Typography>
                  {Object.entries(resolvedInputSchema as Record<string, any>).map(([key, field]: [string, any]) => {
                    const fieldValue = agentOptions[key] ?? '';
                    const isRequired = field.required === true;

                    if (field.type === 'select') {
                      return (
                        <FormControl key={key} fullWidth required={isRequired}>
                          <InputLabel>{field.label}</InputLabel>
                          <Select
                            value={fieldValue}
                            onChange={(e) => setAgentOptions({ ...agentOptions, [key]: e.target.value })}
                            label={field.label}
                          >
                            {field.options?.map((option: any) => (
                              <MenuItem key={option.value} value={option.value}>
                                {option.label}
                              </MenuItem>
                            ))}
                          </Select>
                          {field.description && (
                            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                              {field.description}
                            </Typography>
                          )}
                        </FormControl>
                      );
                    }

                    if (field.type === 'textarea') {
                      return (
                        <TextField
                          key={key}
                          label={field.label}
                          placeholder={field.placeholder}
                          value={fieldValue}
                          onChange={(e) => setAgentOptions({ ...agentOptions, [key]: e.target.value })}
                          multiline
                          rows={field.rows || 3}
                          fullWidth
                          required={isRequired}
                          helperText={field.description}
                        />
                      );
                    }

                    return (
                      <TextField
                        key={key}
                        label={field.label}
                        placeholder={field.placeholder}
                        type={field.type || 'text'}
                        value={fieldValue}
                        onChange={(e) => setAgentOptions({ ...agentOptions, [key]: e.target.value })}
                        fullWidth
                        required={isRequired}
                        helperText={field.description}
                      />
                    );
                  })}
                </Box>
              );
            }

            return (
              <TextField
                fullWidth
                label="Texte d'entrée (optionnel)"
                multiline
                rows={3}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Texte qui complétera le prompt de l'agent..."
                helperText="Laissez vide pour utiliser la description du nœud"
              />
            );
          })()}

          {/* Type de rendu */}
          <FormControl fullWidth>
            <FormLabel>Type de rendu</FormLabel>
            <RadioGroup
              row
              value={outputType}
              onChange={(e) => setOutputType(e.target.value as OutputRenderType)}
              sx={{ flexWrap: 'wrap', gap: 0.5 }}
            >
              <FormControlLabel 
                value="screen" 
                control={<Radio />} 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <ScreenIcon fontSize="small" />
                    <span>À l'écran</span>
                  </Box>
                } 
              />
              <FormControlLabel 
                value="mindmap_child" 
                control={<Radio />} 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <NoteAddIcon fontSize="small" />
                    <span>Nœud enfant (date + titre)</span>
                  </Box>
                } 
              />
              <FormControlLabel 
                value="email" 
                control={<Radio />} 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <EmailIcon fontSize="small" />
                    <span>Par email</span>
                  </Box>
                } 
              />
              <FormControlLabel 
                value="audio_tts" 
                control={<Radio />} 
                label="Audio (TTS)" 
              />
              <FormControlLabel 
                value="audio_email" 
                control={<Radio />} 
                label="Audio par email" 
              />
            </RadioGroup>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
              « Nœud enfant » enregistre le markdown sous le nœud courant avec le titre{' '}
              <strong>AAAA-MM-JJ — nom du nœud</strong> (exécutions manuelles, planifiées et auto).
            </Typography>
          </FormControl>

          {/* Configuration email (Par email ou Audio par email) */}
          {(outputType === 'email' || outputType === 'audio_email') && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
              <TextField
                fullWidth
                label="Destinataire"
                type="email"
                value={emailTo}
                onChange={(e) => setEmailTo(e.target.value)}
                required
              />
              <TextField
                fullWidth
                label="Sujet (optionnel)"
                value={emailSubject}
                onChange={(e) => setEmailSubject(e.target.value)}
              />
            </Box>
          )}

          {/* Résultat ou erreur */}
          {executeError && (
            <Alert severity="error">{executeError}</Alert>
          )}
          {/* Statut, appels d'outils et texte du modèle au fur et à mesure (streaming) */}
          {isExecuting && (streamingStatus || streamingText || streamingToolResults.length > 0) && (
            <Box
              ref={streamContainerRef}
              sx={{
                mt: 2,
                p: 2,
                bgcolor: 'rgba(0, 217, 255, 0.06)',
                borderRadius: 1,
                border: '1px solid rgba(0, 217, 255, 0.2)',
                maxHeight: 420,
                overflow: 'auto',
              }}
            >
              {/* Log d'activité (statuts successifs) */}
              {streamingStatus && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5, color: '#00D9FF' }}>
                    ⏳ Activité
                  </Typography>
                  <Box
                    component="ul"
                    sx={{
                      m: 0,
                      pl: 2,
                      py: 0.5,
                      fontSize: '0.75rem',
                      color: 'text.secondary',
                      lineHeight: 1.6,
                      '& li': { mb: 0.25 },
                    }}
                  >
                    {streamingStatus.split('\n').filter(Boolean).map((line, idx) => (
                      <li key={idx}>{line}</li>
                    ))}
                  </Box>
                </Box>
              )}
              {/* Appels aux outils et réponses */}
              {streamingToolResults.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5, color: '#00D9FF' }}>
                    🔧 Outils utilisés
                  </Typography>
                  {streamingToolResults.map((tr, idx) => (
                    <Box
                      key={idx}
                      sx={{
                        mt: 0.5,
                        p: 1.25,
                        bgcolor: 'rgba(0, 217, 255, 0.06)',
                        borderRadius: 0.5,
                        borderLeft: '3px solid rgba(0, 217, 255, 0.5)',
                      }}
                    >
                      <Typography variant="caption" sx={{ fontWeight: 600, color: '#00D9FF' }}>
                        {tr.toolName}
                      </Typography>
                      <Typography
                        component="pre"
                        sx={{
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          fontSize: '0.75rem',
                          lineHeight: 1.4,
                          color: 'text.secondary',
                          mt: 0.25,
                          maxHeight: 100,
                          overflow: 'auto',
                        }}
                      >
                        {tr.resultPreview}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}
              {/* Réponse du modèle (contenu principal) */}
              <Box>
                <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5, color: '#00D9FF' }}>
                  📝 Réponse {streamingText ? '(en cours…)' : ''}
                </Typography>
                <Typography
                  component="pre"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontSize: '0.875rem',
                    lineHeight: 1.6,
                    color: 'text.primary',
                    fontFamily: 'inherit',
                    m: 0,
                  }}
                >
                  {streamingText}
                </Typography>
              </Box>
            </Box>
          )}
          {executeResult && (
            <Box sx={{ mt: 1 }}>
              <Alert severity={executeResult.success ? 'success' : 'warning'} sx={{ mb: 1 }}>
                {executeResult.message}
                {executeResult.email_sent && (
                  <Typography variant="caption" display="block" sx={{ mt: 0.5, fontWeight: 600 }}>
                    ✉️ Email envoyé avec succès
                  </Typography>
                )}
                {executeResult.output?.execution_time_ms && (
                  <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                    ⏱️ Temps d'exécution: {executeResult.output.execution_time_ms}ms
                  </Typography>
                )}
              </Alert>

              {executeResult.output?.child_node_id && (
                <Alert severity="success" sx={{ mb: 1 }}>
                  Nœud enfant créé :{' '}
                  {executeResult.output.child_node_label ||
                    `n°${executeResult.output.child_node_id}`}
                </Alert>
              )}

              {/* Lecteur audio (TTS) */}
              {executeResult.output?.audio_base64 && (
                <Box sx={{ mt: 2, p: 2, bgcolor: 'rgba(0, 217, 255, 0.08)', borderRadius: 1, border: '1px solid rgba(0, 217, 255, 0.2)' }}>
                  <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600, color: 'text.primary' }}>
                    🔊 Écouter l'audio (TTS)
                  </Typography>
                  <audio
                    controls
                    style={{ width: '100%' }}
                    src={`data:${executeResult.output.audio_mimetype || 'audio/mpeg'};base64,${executeResult.output.audio_base64}`}
                  >
                    Votre navigateur ne prend pas en charge l'audio.
                  </audio>
                </Box>
              )}
              
              {/* Afficher les résultats seulement si l'email n'a pas été envoyé */}
              {executeResult.output && !executeResult.email_sent && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600, color: 'text.primary' }}>
                    📊 Résultats de l'exécution
                  </Typography>
                  
                  {/* Informations générales */}
                  {(executeResult.output.agent_name || executeResult.output.input_text) && (
                    <Box 
                      sx={{ 
                        mb: 2, 
                        p: 1.5, 
                        bgcolor: 'rgba(0, 217, 255, 0.08)',
                        borderRadius: 1,
                        border: '1px solid',
                        borderColor: 'rgba(0, 217, 255, 0.2)',
                      }}
                    >
                      {executeResult.output.agent_name && (
                        <Typography variant="caption" sx={{ display: 'block', mb: 0.5, color: 'text.primary' }}>
                          <strong style={{ color: '#00D9FF' }}>🤖 Agent :</strong>{' '}
                          <span style={{ color: '#E8EDF5' }}>{executeResult.output.agent_name}</span>
                        </Typography>
                      )}
                      {executeResult.output.input_text && (
                        <Typography variant="caption" sx={{ display: 'block', color: 'text.primary' }}>
                          <strong style={{ color: '#00D9FF' }}>📥 Consigne :</strong>{' '}
                          <span style={{ color: '#E8EDF5' }}>{executeResult.output.input_text}</span>
                        </Typography>
                      )}
                    </Box>
                  )}
                  
                  {/* Prompt utilisé */}
                  {executeResult.output.prompt_used && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5, color: 'text.primary' }}>
                        📝 Prompt utilisé:
                      </Typography>
                      <Box
                        sx={{
                          p: 1.5,
                          bgcolor: 'rgba(0, 217, 255, 0.05)',
                          borderRadius: 1,
                          overflow: 'auto',
                          maxHeight: '300px',
                          border: '1px solid',
                          borderColor: 'rgba(0, 217, 255, 0.15)',
                          '& .markdown-body': {
                            color: 'text.secondary',
                            fontSize: '0.75rem',
                            lineHeight: 1.6,
                            '& h1, & h2, & h3, & h4, & h5, & h6': {
                              color: 'text.primary',
                              fontWeight: 600,
                              marginTop: '0.75em',
                              marginBottom: '0.4em',
                            },
                            '& h1': {
                              fontSize: '1.2rem',
                              borderBottom: '1px solid rgba(0, 217, 255, 0.2)',
                              paddingBottom: '0.3em',
                            },
                            '& h2': {
                              fontSize: '1.1rem',
                              borderBottom: '1px solid rgba(0, 217, 255, 0.15)',
                              paddingBottom: '0.3em',
                            },
                            '& h3': {
                              fontSize: '1rem',
                            },
                            '& p': {
                              marginBottom: '0.5em',
                              color: 'text.secondary',
                            },
                            '& ul, & ol': {
                              marginBottom: '0.5em',
                              paddingLeft: '1.5em',
                              color: 'text.secondary',
                            },
                            '& li': {
                              marginBottom: '0.25em',
                            },
                            '& strong': {
                              color: '#00D9FF',
                              fontWeight: 600,
                            },
                            '& a': {
                              color: '#00D9FF',
                              textDecoration: 'none',
                              '&:hover': {
                                textDecoration: 'underline',
                              },
                            },
                            '& code': {
                              backgroundColor: 'rgba(0, 0, 0, 0.3)',
                              padding: '0.2em 0.4em',
                              borderRadius: '3px',
                              fontSize: '0.9em',
                              fontFamily: 'monospace',
                              color: '#5CE1FF',
                            },
                            '& pre': {
                              backgroundColor: 'rgba(0, 0, 0, 0.3)',
                              padding: '0.75em',
                              borderRadius: '4px',
                              overflow: 'auto',
                              '& code': {
                                backgroundColor: 'transparent',
                                padding: 0,
                              },
                            },
                            '& blockquote': {
                              borderLeft: '4px solid rgba(0, 217, 255, 0.3)',
                              paddingLeft: '1em',
                              marginLeft: 0,
                              color: 'text.secondary',
                              fontStyle: 'italic',
                            },
                          },
                        }}
                      >
                        <ReactMarkdown className="markdown-body">
                          {executeResult.output.prompt_used}
                        </ReactMarkdown>
                      </Box>
                    </Box>
                  )}
                  
                  {/* Sortie brute (Markdown formaté) */}
                  {executeResult.output.output_raw && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5, color: 'text.primary' }}>
                        📤 Réponse de l'agent (Markdown):
                      </Typography>
                      <Box
                        sx={{
                          p: 1.5,
                          bgcolor: 'rgba(139, 149, 168, 0.08)',
                          borderRadius: 1,
                          overflow: 'auto',
                          maxHeight: '400px',
                          border: '1px solid',
                          borderColor: 'rgba(139, 149, 168, 0.2)',
                          '& .markdown-body': {
                            color: 'text.primary',
                            fontSize: '0.875rem',
                            lineHeight: 1.6,
                            '& h1, & h2, & h3, & h4, & h5, & h6': {
                              color: 'text.primary',
                              fontWeight: 600,
                              marginTop: '1em',
                              marginBottom: '0.5em',
                            },
                            '& h1': {
                              fontSize: '1.5rem',
                              borderBottom: '1px solid rgba(139, 149, 168, 0.2)',
                              paddingBottom: '0.3em',
                            },
                            '& h2': {
                              fontSize: '1.25rem',
                              borderBottom: '1px solid rgba(139, 149, 168, 0.15)',
                              paddingBottom: '0.3em',
                            },
                            '& h3': {
                              fontSize: '1.1rem',
                            },
                            '& p': {
                              marginBottom: '0.75em',
                              color: 'text.primary',
                            },
                            '& ul, & ol': {
                              marginBottom: '0.75em',
                              paddingLeft: '1.5em',
                              color: 'text.primary',
                            },
                            '& li': {
                              marginBottom: '0.25em',
                            },
                            '& strong': {
                              color: '#00D9FF',
                              fontWeight: 600,
                            },
                            '& a': {
                              color: '#00D9FF',
                              textDecoration: 'none',
                              '&:hover': {
                                textDecoration: 'underline',
                              },
                            },
                            '& code': {
                              backgroundColor: 'rgba(0, 0, 0, 0.3)',
                              padding: '0.2em 0.4em',
                              borderRadius: '3px',
                              fontSize: '0.9em',
                              fontFamily: 'monospace',
                              color: '#5CE1FF',
                            },
                            '& pre': {
                              backgroundColor: 'rgba(0, 0, 0, 0.3)',
                              padding: '1em',
                              borderRadius: '4px',
                              overflow: 'auto',
                              '& code': {
                                backgroundColor: 'transparent',
                                padding: 0,
                              },
                            },
                            '& blockquote': {
                              borderLeft: '4px solid rgba(0, 217, 255, 0.3)',
                              paddingLeft: '1em',
                              marginLeft: 0,
                              color: 'text.secondary',
                              fontStyle: 'italic',
                            },
                            '& table': {
                              borderCollapse: 'collapse',
                              width: '100%',
                              marginBottom: '1em',
                              '& th, & td': {
                                border: '1px solid rgba(139, 149, 168, 0.2)',
                                padding: '0.5em',
                                textAlign: 'left',
                              },
                              '& th': {
                                backgroundColor: 'rgba(0, 217, 255, 0.1)',
                                fontWeight: 600,
                                color: '#00D9FF',
                              },
                            },
                          },
                        }}
                      >
                        <ReactMarkdown className="markdown-body">
                          {getAgentResponseMarkdownForDisplay(executeResult.output)}
                        </ReactMarkdown>
                      </Box>
                    </Box>
                  )}
                  
                  {/* Sortie parsée - affichée seulement si différente de la sortie brute */}
                  {executeResult.output.output_parsed && 
                   executeResult.output.output_parsed.markdown && 
                   executeResult.output.output_parsed.markdown !== executeResult.output.output_raw && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5, color: 'text.primary' }}>
                        📋 Données structurées (JSON):
                      </Typography>
                      <Box
                        component="pre"
                        sx={{
                          p: 1.5,
                          bgcolor: 'rgba(74, 222, 128, 0.08)',
                          borderRadius: 1,
                          fontSize: '0.75rem',
                          overflow: 'auto',
                          maxHeight: '300px',
                          border: '1px solid',
                          borderColor: 'rgba(74, 222, 128, 0.2)',
                          color: 'text.primary',
                          fontFamily: 'monospace',
                          lineHeight: 1.6,
                        }}
                      >
                        {JSON.stringify(executeResult.output.output_parsed, null, 2)}
                      </Box>
                    </Box>
                  )}
                  
                  {/* Si la sortie parsée contient du markdown identique à la sortie brute, ne pas l'afficher */}
                  {executeResult.output.output_parsed && 
                   executeResult.output.output_parsed.markdown && 
                   executeResult.output.output_parsed.markdown === executeResult.output.output_raw && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" sx={{ fontWeight: 400, display: 'block', mb: 0.5, color: 'text.secondary', fontStyle: 'italic' }}>
                        ℹ️ La réponse a été détectée comme Markdown et est affichée ci-dessus.
                      </Typography>
                    </Box>
                  )}
                  
                  {/* Si la sortie parsée existe mais n'est pas du markdown (JSON structuré) */}
                  {executeResult.output.output_parsed &&
                   !executeResult.output.output_parsed.markdown &&
                   !shouldRenderNewsMonitorMarkdown(
                     executeResult.output.output_parsed as Record<string, unknown>,
                   ) && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5, color: 'text.primary' }}>
                        📋 Données structurées (JSON):
                      </Typography>
                      <Box
                        component="pre"
                        sx={{
                          p: 1.5,
                          bgcolor: 'rgba(74, 222, 128, 0.08)',
                          borderRadius: 1,
                          fontSize: '0.75rem',
                          overflow: 'auto',
                          maxHeight: '300px',
                          border: '1px solid',
                          borderColor: 'rgba(74, 222, 128, 0.2)',
                          color: 'text.primary',
                          fontFamily: 'monospace',
                          lineHeight: 1.6,
                        }}
                      >
                        {JSON.stringify(executeResult.output.output_parsed, null, 2)}
                      </Box>
                    </Box>
                  )}
                  
                  
                  {/* Message si pas de sortie parsée */}
                  {!executeResult.output.output_parsed && executeResult.output.output_raw && (
                    <Alert severity="warning" sx={{ mt: 1 }}>
                      ⚠️ La sortie n'a pas pu être parsée selon le schéma attendu. Voir la sortie brute ci-dessus.
                    </Alert>
                  )}
                </Box>
              )}

              {executeResult.success &&
                taskType === 'agent' &&
                outputType === 'screen' &&
                !executeResult.email_sent &&
                !executeResult.output?.child_node_id &&
                extractMarkdownFromExecuteOutput(executeResult.output) && (
                  <Box
                    sx={{
                      mt: 2,
                      p: 2,
                      borderRadius: 1,
                      border: '1px dashed',
                      borderColor: 'rgba(0, 217, 255, 0.35)',
                      bgcolor: 'rgba(0, 217, 255, 0.04)',
                    }}
                  >
                    <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600, color: 'text.primary' }}>
                      Enregistrer le rendu dans le mindmap
                    </Typography>
                    <Typography variant="caption" sx={{ display: 'block', mb: 1.5, color: 'text.secondary' }}>
                      Crée un nœud enfant sous « {selectedNode.data.label} » avec le markdown dans la description. Par défaut :{' '}
                      {buildDefaultResultChildLabel(selectedNode.data.label || '')}.
                    </Typography>
                    <TextField
                      fullWidth
                      size="small"
                      label="Titre du nœud"
                      placeholder={buildDefaultResultChildLabel(selectedNode.data.label || '')}
                      value={resultChildLabel}
                      onChange={(e) => setResultChildLabel(e.target.value)}
                      sx={{ mb: 1.5 }}
                    />
                    <Button
                      variant="outlined"
                      color="primary"
                      startIcon={savingResultChild ? <CircularProgress size={16} /> : <NoteAddIcon />}
                      onClick={handleCreateResultChildNode}
                      disabled={savingResultChild || !selectedNode.data.backendId}
                      sx={{ textTransform: 'none' }}
                    >
                      {savingResultChild ? 'Création…' : 'Créer un nœud enfant avec ce rendu'}
                    </Button>
                  </Box>
                )}
              
              {/* Message si l'email a été envoyé */}
              {executeResult.email_sent && (
                <Alert severity="success" sx={{ mt: 1 }}>
                  ✉️ Le résultat a été envoyé par email. Vérifiez votre boîte de réception.
                </Alert>
              )}
            </Box>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCloseManualExecute} disabled={isExecuting}>
          {executeResult ? 'Fermer' : 'Annuler'}
        </Button>
        {!executeResult && (
          <Button
            onClick={handleExecuteTrigger}
            variant="contained"
            startIcon={isExecuting ? <CircularProgress size={16} /> : <PlayIcon />}
            disabled={isExecuting || (taskType === 'agent' && !selectedAgent) || (taskType === 'action' && !selectedAction)}
          >
            {isExecuting ? 'Exécution...' : 'Lancer'}
          </Button>
        )}
      </DialogActions>
    </Dialog>

    <Dialog
      open={descriptionMdDialogOpen}
      onClose={() => setDescriptionMdDialogOpen(false)}
      maxWidth="md"
      fullWidth
      scroll="paper"
      PaperProps={{ sx: { maxHeight: '92vh' } }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 1,
          pr: 1,
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0, pt: 0.25 }}>Afficher le descriptif</Box>
        <IconButton
          aria-label="Fermer la fenêtre"
          onClick={() => setDescriptionMdDialogOpen(false)}
          edge="end"
          size="small"
          sx={{ color: 'text.secondary', flexShrink: 0, mt: -0.25 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers sx={{ pt: 2 }}>
        <Box
          sx={{
            minHeight: 200,
            maxHeight: 'calc(92vh - 160px)',
            overflow: 'auto',
            p: 1.5,
            bgcolor: 'rgba(139, 149, 168, 0.08)',
            borderRadius: 1,
            border: '1px solid rgba(139, 149, 168, 0.2)',
            '& .markdown-body': {
              color: 'text.primary',
              fontSize: '0.9375rem',
              lineHeight: 1.65,
              '& h1, & h2, & h3': { color: 'text.primary', fontWeight: 600, mt: 1.25, mb: 0.5 },
              '& p': { mb: 0.85 },
              '& ul, & ol': { pl: 2.5, mb: 0.85 },
              '& code': {
                bgcolor: 'rgba(0,0,0,0.3)',
                px: 0.5,
                borderRadius: 0.5,
                fontSize: '0.9em',
              },
              '& pre': { bgcolor: 'rgba(0,0,0,0.25)', p: 1.25, borderRadius: 1, overflow: 'auto' },
              '& a': { color: '#00D9FF' },
              '& table': { borderCollapse: 'collapse', width: '100%', '& th, & td': { border: '1px solid rgba(139,149,168,0.25)', p: 0.75 } },
            },
          }}
        >
          <ReactMarkdown className="markdown-body">{editDescription}</ReactMarkdown>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setDescriptionMdDialogOpen(false)} variant="contained" sx={{ textTransform: 'none' }}>
          Fermer
        </Button>
      </DialogActions>
    </Dialog>

    {/* Boîte de configuration du trigger */}
    {selectedNode?.data?.backendId && (
      <TriggerForm
        open={triggerFormOpen}
        nodeId={String(selectedNode.data.backendId)}
        trigger={editingTrigger}
        onClose={() => {
          setTriggerFormOpen(false);
          setEditingTrigger(null);
          // Recharger le mindmap après fermeture pour avoir les données à jour
          if (currentMindmap) {
            loadNodes(currentMindmap.id);
          }
        }}
        onSave={async () => {
          // Recharger le mindmap après sauvegarde
          if (currentMindmap) {
            await loadNodes(currentMindmap.id);
            // Mettre à jour selectedNode avec les nouvelles données
            const store = useMindmapStore.getState();
            const updatedNode = store.nodes.find(n => n.id === selectedNode.id);
            if (updatedNode) {
              setSelectedNode(updatedNode);
            }
          }
        }}
      />
    )}
    </>
  );
};

export default NodeDetails;
