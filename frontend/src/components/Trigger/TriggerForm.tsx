import { useState, useEffect } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormControlLabel,
  Switch,
  Typography,
  RadioGroup,
  Radio,
  FormLabel,
  Divider,
  Chip,
} from "@mui/material";
import { configurableAgentsApi } from "../../services/api";
import type { ConfigurableAgentResponse } from "../../services/api";
import { loadAgentsFromFiles } from "../../api/client";
import { useNotification } from "../../hooks/useNotification";

type TriggerType = "email_received" | "date_reached" | "cron" | "state_changed" | "manual";

interface TriggerFormProps {
  open: boolean;
  nodeId: string;
  trigger?: {
    id: string;
    trigger_type: TriggerType;
    config: Record<string, any>;
    enabled: boolean;
  } | null;
  onClose: () => void;
  onSave: (newTrigger?: any) => void;
}

const TRIGGER_TYPES: { value: TriggerType; label: string }[] = [
  { value: "email_received", label: "Email reçu" },
  { value: "date_reached", label: "Date atteinte" },
  { value: "cron", label: "Cron (planifié)" },
  { value: "state_changed", label: "Changement d'état" },
  { value: "manual", label: "Manuel" },
];

export default function TriggerForm({
  open,
  nodeId,
  trigger,
  onClose,
  onSave,
}: TriggerFormProps) {
  const [triggerType, setTriggerType] = useState<TriggerType>("manual");
  const [enabled, setEnabled] = useState(true);
  const [config, setConfig] = useState<Record<string, any>>({});
  const { showSuccess, showError } = useNotification();
  
  // États pour la configuration de l'exécution
  const [taskType, setTaskType] = useState<'agent' | 'action'>('agent');
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [selectedAction, setSelectedAction] = useState<string>('');
  const [inputText, setInputText] = useState('');
  const [outputType, setOutputType] = useState<'screen' | 'email'>('screen');
  const [emailTo, setEmailTo] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [availableAgents, setAvailableAgents] = useState<ConfigurableAgentResponse[]>([]);
  const [availableActions, setAvailableActions] = useState<ActionResponse[]>([]);
  const [agentOptions, setAgentOptions] = useState<Record<string, any>>({});

  // Charger les agents et actions disponibles
  useEffect(() => {
    if (open) {
      loadAvailableAgents();
      loadAvailableActions();
    }
  }, [open, nodeId]);

  const loadAvailableAgents = async () => {
    try {
      console.log('[TriggerForm] Chargement des agents...');
      const response = await configurableAgentsApi.list();
      console.log('[TriggerForm] Agents reçus:', response.agents);
      console.log('[TriggerForm] Détails des agents:', response.agents?.map(a => ({
        id: a.id,
        name: a.name,
        hasInputSchema: !!a.input_schema,
        inputSchemaKeys: a.input_schema ? Object.keys(a.input_schema) : []
      })));
      setAvailableAgents(response.agents || []);
      if (!response.agents || response.agents.length === 0) {
        console.warn('[TriggerForm] Aucun agent disponible');
      }
    } catch (error) {
      console.error('[TriggerForm] Erreur lors du chargement des agents:', error);
      setAvailableAgents([]);
    }
  };

  const loadAvailableActions = async () => {
    try {
      // Charger les actions du nœud (pour les actions de type "reminder")
      const { listActions } = await import("../../api/client");
      const response = await listActions(nodeId);
      const nodeActions = response.actions || [];
      
      // Filtrer pour ne garder que les actions de type "reminder"
      const reminderActions = nodeActions.filter((action: any) => action.action_type === "reminder");
      setAvailableActions(reminderActions);
    } catch (error) {
      console.error('Erreur lors du chargement des actions:', error);
      setAvailableActions([]);
    }
  };

  // Fonction pour générer l'expression cron à partir des paramètres
  const generateCronExpression = (updatedConfig: Record<string, any>) => {
    const days = updatedConfig.cron_days || [];
    const hour = updatedConfig.cron_hour ?? 9;
    const minute = updatedConfig.cron_minute ?? 0;
    
    let cronExpr: string;
    
    if (days.length === 0 || days.length === 7) {
      // Si aucun jour n'est sélectionné ou tous les jours, utiliser *
      cronExpr = `${minute} ${hour} * * *`;
    } else {
      // Jours spécifiques (0 = dimanche, 6 = samedi).
      // NOTE: cette convention est alignée avec le backend (APScheduler) et les expressions cron standard.
      // Toute évolution UI (ex: afficher Lundi=1) doit conserver ce mapping, sinon on introduit des décalages.
      const daysStr = days.sort((a: number, b: number) => a - b).join(',');
      cronExpr = `${minute} ${hour} * * ${daysStr}`;
    }
    
    // Source de vérité persistée : `cron_expression`.
    // Les champs UI (cron_hour/cron_minute/cron_days) ne sont que des helpers pour l'édition.
    setConfig({ ...updatedConfig, cron_expression: cronExpr });
  };

  useEffect(() => {
    if (trigger) {
      setTriggerType(trigger.trigger_type);
      setEnabled(trigger.enabled);
      const triggerConfig = trigger.config || {};
      setConfig(triggerConfig);
      
      // Si c'est un trigger cron et qu'on a une expression mais pas les paramètres détaillés,
      // essayer de parser l'expression pour remplir les champs
      if (trigger.trigger_type === 'cron' && triggerConfig.cron_expression && 
          (!triggerConfig.cron_days && triggerConfig.cron_hour === undefined && triggerConfig.cron_minute === undefined)) {
        // Parser l'expression cron basique: "minute heure * * jours"
        const cronParts = triggerConfig.cron_expression.split(' ');
        if (cronParts.length >= 5) {
          const minute = parseInt(cronParts[0]) || 0;
          const hour = parseInt(cronParts[1]) || 9;
          const daysPart = cronParts[4];
          
          let days: number[] = [];
          if (daysPart === '*') {
            // Tous les jours
            days = [0, 1, 2, 3, 4, 5, 6];
          } else {
            // Parser les jours (peut être "1,2,3" ou "1-5")
            const dayRanges = daysPart.split(',');
            dayRanges.forEach(range => {
              if (range.includes('-')) {
                const [start, end] = range.split('-').map(Number);
                for (let i = start; i <= end; i++) {
                  if (i >= 0 && i <= 6) days.push(i);
                }
              } else {
                const day = parseInt(range);
                if (day >= 0 && day <= 6) days.push(day);
              }
            });
          }
          
          triggerConfig.cron_minute = minute;
          triggerConfig.cron_hour = hour;
          triggerConfig.cron_days = days;
          setConfig(triggerConfig);
        }
      }
      
      // Si c'est un trigger cron et qu'on a les paramètres mais pas l'expression, la générer
      if (trigger.trigger_type === 'cron' && 
          (triggerConfig.cron_days || triggerConfig.cron_hour !== undefined || triggerConfig.cron_minute !== undefined) &&
          !triggerConfig.cron_expression) {
        generateCronExpression(triggerConfig);
      }
      
      // Restaurer les valeurs de configuration d'exécution
      setTaskType(triggerConfig.task_type || 'agent');
      setSelectedAgent(triggerConfig.selected_agent || '');
      setSelectedAction(triggerConfig.selected_action || '');
      setInputText(triggerConfig.input_text || '');
      setOutputType(triggerConfig.output_type || 'screen');
      setEmailTo(triggerConfig.email_to || '');
      setEmailSubject(triggerConfig.email_subject || '');
      // Restaurer les options de l'agent (champs dynamiques)
      setAgentOptions(triggerConfig.agent_options || {});
    } else {
      setTriggerType("manual");
      setEnabled(true);
      setConfig({});
      setTaskType('agent');
      setSelectedAgent('');
      setSelectedAction('');
      setInputText('');
      setOutputType('screen');
      setEmailTo('');
      setEmailSubject('');
      setAgentOptions({});
    }
  }, [trigger, open]);

  const getConfigFields = () => {
    switch (triggerType) {
      case "date_reached":
        // Convertir la date ISO en format datetime-local si elle existe
        let dateValue = "";
        if (config.run_at) {
          try {
            const date = new Date(config.run_at);
            if (!isNaN(date.getTime())) {
              // Format: YYYY-MM-DDTHH:mm pour datetime-local
              dateValue = date.toISOString().slice(0, 16);
            }
          } catch (e) {
            console.error("Erreur lors de la conversion de la date:", e);
          }
        }
        return (
          <>
            <TextField
              fullWidth
              label="Date d'exécution"
              type="datetime-local"
              value={dateValue}
              onChange={(e) => {
                // Convertir en format ISO pour le backend
                const localDate = e.target.value;
                if (localDate) {
                  const isoDate = new Date(localDate).toISOString();
                  setConfig({ ...config, run_at: isoDate });
                } else {
                  setConfig({ ...config, run_at: undefined });
                }
              }}
              InputLabelProps={{ shrink: true }}
              sx={{ mt: 2 }}
            />
          </>
        );
      case "cron":
        // Valeurs par défaut pour la planification
        const cronDays = config.cron_days || [];
        const cronHour = config.cron_hour || 9;
        const cronMinute = config.cron_minute || 0;
        
        const DAYS_OF_WEEK = [
          { value: 0, label: "Dimanche" },
          { value: 1, label: "Lundi" },
          { value: 2, label: "Mardi" },
          { value: 3, label: "Mercredi" },
          { value: 4, label: "Jeudi" },
          { value: 5, label: "Vendredi" },
          { value: 6, label: "Samedi" },
        ];
        
        return (
          <>
            <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="body2" fontWeight={500}>
                Planification
              </Typography>
              
              {/* Heure */}
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <FormControl sx={{ minWidth: 100 }}>
                  <InputLabel>Heure</InputLabel>
                  <Select
                    value={cronHour}
                    label="Heure"
                    onChange={(e) => {
                      const hour = Number(e.target.value);
                      setConfig({ ...config, cron_hour: hour });
                      // Générer l'expression cron automatiquement
                      generateCronExpression({ ...config, cron_hour: hour });
                    }}
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <MenuItem key={i} value={i}>
                        {String(i).padStart(2, '0')}h
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                
                <FormControl sx={{ minWidth: 100 }}>
                  <InputLabel>Minute</InputLabel>
                  <Select
                    value={cronMinute}
                    label="Minute"
                    onChange={(e) => {
                      const minute = Number(e.target.value);
                      setConfig({ ...config, cron_minute: minute });
                      generateCronExpression({ ...config, cron_minute: minute });
                    }}
                  >
                    {Array.from({ length: 60 }, (_, i) => (
                      <MenuItem key={i} value={i}>
                        {String(i).padStart(2, '0')}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>
              
              {/* Jours de la semaine */}
              <FormControl fullWidth>
                <InputLabel>Jours de la semaine</InputLabel>
                <Select
                  multiple
                  value={cronDays}
                  label="Jours de la semaine"
                  onChange={(e) => {
                    const days = typeof e.target.value === 'string' 
                      ? e.target.value.split(',').map(Number)
                      : e.target.value as number[];
                    setConfig({ ...config, cron_days: days });
                    generateCronExpression({ ...config, cron_days: days });
                  }}
                  renderValue={(selected) => {
                    if (selected.length === 0) return "Aucun jour sélectionné";
                    if (selected.length === 7) return "Tous les jours";
                    return selected
                      .sort((a, b) => a - b)
                      .map(day => DAYS_OF_WEEK[day].label)
                      .join(', ');
                  }}
                >
                  {DAYS_OF_WEEK.map((day) => (
                    <MenuItem key={day.value} value={day.value}>
                      {day.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              {/* Expression cron générée (en lecture seule) */}
              <TextField
                fullWidth
                label="Expression Cron (générée automatiquement)"
                value={config.cron_expression || ""}
                InputProps={{ readOnly: true }}
                helperText="Cette expression est générée automatiquement à partir de vos sélections"
                sx={{ mt: 1 }}
              />
              
              {/* Option pour expression manuelle */}
              <FormControlLabel
                control={
                  <Switch
                    checked={config.manual_cron || false}
                    onChange={(e) => {
                      setConfig({ ...config, manual_cron: e.target.checked });
                    }}
                  />
                }
                label="Utiliser une expression cron manuelle"
              />
              
              {config.manual_cron && (
                <TextField
                  fullWidth
                  label="Expression Cron (manuelle)"
                  placeholder="0 9 * * * (tous les jours à 9h)"
                  value={config.cron_expression || ""}
                  onChange={(e) =>
                    setConfig({ ...config, cron_expression: e.target.value })
                  }
                  helperText="Format: minute heure jour mois jour-semaine (ex: 0 9 * * 1-5 pour du lundi au vendredi à 9h)"
                />
              )}
            </Box>
          </>
        );
      case "state_changed":
        return (
          <>
            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel>État déclencheur</InputLabel>
              <Select
                value={config.from_status || ""}
                onChange={(e) =>
                  setConfig({ ...config, from_status: e.target.value })
                }
                label="État déclencheur"
              >
                <MenuItem value="inbox">Inbox</MenuItem>
                <MenuItem value="ready">Ready</MenuItem>
                <MenuItem value="doing">Doing</MenuItem>
                <MenuItem value="waiting">Waiting</MenuItem>
                <MenuItem value="done">Done</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel>État cible</InputLabel>
              <Select
                value={config.to_status || ""}
                onChange={(e) =>
                  setConfig({ ...config, to_status: e.target.value })
                }
                label="État cible"
              >
                <MenuItem value="inbox">Inbox</MenuItem>
                <MenuItem value="ready">Ready</MenuItem>
                <MenuItem value="doing">Doing</MenuItem>
                <MenuItem value="waiting">Waiting</MenuItem>
                <MenuItem value="done">Done</MenuItem>
              </Select>
            </FormControl>
          </>
        );
      case "email_received":
        return (
          <>
            <TextField
              fullWidth
              label="Expéditeur (optionnel)"
              placeholder="contact@example.com"
              value={config.from_email || ""}
              onChange={(e) =>
                setConfig({ ...config, from_email: e.target.value })
              }
              sx={{ mt: 2 }}
            />
            <TextField
              fullWidth
              label="Sujet contient (optionnel)"
              value={config.subject_contains || ""}
              onChange={(e) =>
                setConfig({ ...config, subject_contains: e.target.value })
              }
              sx={{ mt: 2 }}
            />
          </>
        );
      default:
        return (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Ce trigger peut être lancé manuellement via le bouton "Lancer".
          </Typography>
        );
    }
  };

  const handleSave = async () => {
    console.log("[TriggerForm] handleSave appelé");
    console.log("[TriggerForm] trigger:", trigger);
    console.log("[TriggerForm] triggerType:", triggerType);
    console.log("[TriggerForm] config:", config);
    console.log("[TriggerForm] enabled:", enabled);
    
    // Construire la config complète avec les paramètres d'exécution
    const fullConfig = {
      ...config,
      task_type: taskType,
      selected_agent: taskType === 'agent' ? selectedAgent : undefined,
      selected_action: taskType === 'action' ? selectedAction : undefined,
      input_text: inputText || undefined,
      agent_options: taskType === 'agent' && Object.keys(agentOptions).length > 0 ? agentOptions : undefined,
      output_type: outputType,
      email_to: outputType === 'email' ? emailTo : undefined,
      email_subject: outputType === 'email' ? emailSubject : undefined,
    };
    
    const { createTrigger, updateTrigger } = await import("../../api/client");
    
    try {
      if (trigger) {
        // Mise à jour : fermer après sauvegarde
        console.log("[TriggerForm] Mode mise à jour du trigger:", trigger.id);
        await updateTrigger(trigger.id, { 
          trigger_type: triggerType,  // Sauvegarder le type de trigger
          config: fullConfig, 
          enabled 
        });
        console.log("[TriggerForm] Trigger mis à jour, appel de onSave()");
        await onSave();
        console.log("[TriggerForm] Fermeture du formulaire");
        onClose();
        showSuccess("Trigger mis à jour avec succès");
      } else {
        // Création : créer le trigger
        console.log("[TriggerForm] Mode création avec nodeId:", nodeId);
        const newTrigger = await createTrigger({
          node_id: nodeId,
          trigger_type: triggerType,
          config: fullConfig,
          enabled,
        });
        console.log("[TriggerForm] Trigger créé:", newTrigger);
        // Notifier le parent avec le nouveau trigger
        console.log("[TriggerForm] Appel de onSave(newTrigger)");
        await onSave(newTrigger);
        console.log("[TriggerForm] onSave terminé, fermeture du formulaire");
        // Fermer le formulaire
        onClose();
        console.log("[TriggerForm] Formulaire fermé");
        showSuccess("Trigger créé avec succès");
      }
    } catch (error) {
      console.error("[TriggerForm] Erreur lors de la sauvegarde du trigger:", error);
      showError("Erreur lors de la sauvegarde du trigger");
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {trigger ? "Configurer le trigger" : "Créer un trigger"}
      </DialogTitle>
      <DialogContent>
        <FormControl fullWidth sx={{ mt: 1 }}>
          <InputLabel>Type de trigger</InputLabel>
          <Select
            value={triggerType}
            onChange={(e) => {
              const newType = e.target.value as TriggerType;
              setTriggerType(newType);
              // Réinitialiser la config si on change de type
              if (triggerType !== newType) {
                setConfig({});
              }
            }}
            label="Type de trigger"
          >
            {TRIGGER_TYPES.map((type) => (
              <MenuItem key={type.value} value={type.value}>
                {type.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {getConfigFields()}

        <FormControlLabel
          control={
            <Switch
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
          }
          label="Activer le trigger"
          sx={{ mt: 2 }}
        />

        <Divider sx={{ my: 3 }} />
        <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
          Configuration de l'exécution
        </Typography>

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
            }}
          >
            <FormControlLabel value="agent" control={<Radio />} label="Agent" />
            <FormControlLabel value="action" control={<Radio />} label="Action" />
          </RadioGroup>
        </FormControl>

        {/* Sélection de l'agent ou action */}
        <FormControl fullWidth sx={{ mt: 2 }}>
          <InputLabel>
            {taskType === 'agent' ? 'Sélectionner un agent' : 'Sélectionner une action'}
          </InputLabel>
          <Select
            value={taskType === 'agent' ? selectedAgent : selectedAction}
            label={taskType === 'agent' ? 'Sélectionner un agent' : 'Sélectionner une action'}
            onChange={(e) => {
              if (taskType === 'agent') {
                setSelectedAgent(e.target.value);
                setConfig({ ...config, selected_agent: e.target.value, task_type: 'agent' });
                // Réinitialiser les options de l'agent quand on change d'agent
                setAgentOptions({});
              } else {
                setSelectedAction(e.target.value);
                setConfig({ ...config, selected_action: e.target.value, task_type: 'action' });
              }
            }}
          >
            {taskType === 'agent' ? (
              availableAgents.length > 0 ? (
                availableAgents.map((agent) => (
                  <MenuItem key={agent.id} value={String(agent.id)}>
                    <Box>
                      <Typography variant="body2" fontWeight={500}>
                        {agent.name}
                        {agent.input_schema && Object.keys(agent.input_schema).length > 0 && (
                          <Chip 
                            label={`${Object.keys(agent.input_schema).length} paramètre(s)`} 
                            size="small" 
                            sx={{ ml: 1 }} 
                            color="primary"
                          />
                        )}
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
                <MenuItem disabled value="">
                  <Typography variant="body2" color="text.secondary">
                    Aucun agent disponible
                  </Typography>
                </MenuItem>
              )
            ) : (
              <>
                {availableActions.length > 0 ? (
                  availableActions.map((action: any) => (
                    <MenuItem key={action.id} value={String(action.id)}>
                      <Box>
                        <Typography variant="body2" fontWeight={500}>
                          {action.action_type === "reminder" ? "Rappel" : action.action_type}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {action.action_type === "reminder" ? "Formate le mail d'échéance" : action.action_type}
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))
                ) : (
                  <MenuItem disabled value="">
                    <Typography variant="body2" color="text.secondary">
                      Aucune action "Rappel" disponible
                    </Typography>
                  </MenuItem>
                )}
                {/* Option pour créer une action "reminder" si elle n'existe pas */}
                {availableActions.length === 0 && (
                  <Box sx={{ mt: 1, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                      Aucune action "Rappel" n'existe pour ce nœud.
                    </Typography>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={async () => {
                        try {
                          const { createAction } = await import("../../api/client");
                          const newAction = await createAction({
                            node_id: nodeId,
                            action_type: "reminder",
                            mode: "auto",
                            config: {},
                            enabled: true,
                          });
                          showSuccess("Action 'Rappel' créée avec succès");
                          await loadAvailableActions();
                          // Sélectionner automatiquement la nouvelle action
                          setSelectedAction(String(newAction.id));
                          setConfig({ ...config, selected_action: String(newAction.id), task_type: 'action' });
                        } catch (error: any) {
                          console.error('Erreur lors de la création de l\'action:', error);
                          showError("Erreur lors de la création de l'action 'Rappel'");
                        }
                      }}
                    >
                      Créer une action "Rappel"
                    </Button>
                  </Box>
                )}
              </>
            )}
          </Select>
          {taskType === 'agent' && availableAgents.length === 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                Aucun agent configuré.
              </Typography>
              <Button
                size="small"
                variant="outlined"
                onClick={async () => {
                  try {
                    const result = await loadAgentsFromFiles();
                    alert(`${result.loaded} agent(s) chargé(s) depuis les fichiers`);
                    await loadAvailableAgents();
                  } catch (error: any) {
                    alert(`Erreur: ${error.message || "Erreur lors du chargement"}`);
                  }
                }}
              >
                Charger les agents depuis les fichiers
              </Button>
            </Box>
          )}
        </FormControl>

        {/* Champs dynamiques de l'agent ou texte d'entrée générique */}
        {taskType === 'agent' && selectedAgent && (() => {
          const selectedAgentData = availableAgents.find(a => String(a.id) === selectedAgent);
          console.log('[TriggerForm] Agent sélectionné:', selectedAgent);
          console.log('[TriggerForm] Données de l\'agent:', selectedAgentData);
          console.log('[TriggerForm] input_schema:', selectedAgentData?.input_schema);
          
          const hasInputSchema = selectedAgentData?.input_schema && Object.keys(selectedAgentData.input_schema).length > 0;
          console.log('[TriggerForm] hasInputSchema:', hasInputSchema);
          
          if (hasInputSchema) {
            // Afficher les champs dynamiques basés sur l'input_schema
            return (
              <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Paramètres de l'agent
                </Typography>
                {Object.entries(selectedAgentData.input_schema).map(([key, field]: [string, any]) => {
                  const fieldValue = agentOptions[key] || "";
                  const isRequired = field.required === true;

                  if (field.type === "select") {
                    return (
                      <FormControl key={key} fullWidth required={isRequired}>
                        <InputLabel>{field.label}</InputLabel>
                        <Select
                          value={fieldValue}
                          onChange={(e) => {
                            const newOptions = { ...agentOptions, [key]: e.target.value };
                            setAgentOptions(newOptions);
                            setConfig({ ...config, agent_options: newOptions });
                          }}
                          label={field.label}
                        >
                          {field.options?.map((option: any) => (
                            <MenuItem key={option.value} value={option.value}>
                              {option.label}
                            </MenuItem>
                          ))}
                        </Select>
                        {field.description && (
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                            {field.description}
                          </Typography>
                        )}
                      </FormControl>
                    );
                  }

                  if (field.type === "textarea") {
                    return (
                      <TextField
                        key={key}
                        label={field.label}
                        placeholder={field.placeholder}
                        value={fieldValue}
                        onChange={(e) => {
                          const newOptions = { ...agentOptions, [key]: e.target.value };
                          setAgentOptions(newOptions);
                          setConfig({ ...config, agent_options: newOptions });
                        }}
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
                      type={field.type || "text"}
                      value={fieldValue}
                      onChange={(e) => {
                        const newOptions = { ...agentOptions, [key]: e.target.value };
                        setAgentOptions(newOptions);
                        setConfig({ ...config, agent_options: newOptions });
                      }}
                      fullWidth
                      required={isRequired}
                      helperText={field.description}
                    />
                  );
                })}
              </Box>
            );
          } else {
            // Afficher le champ texte générique si pas d'input_schema
            return (
              <TextField
                fullWidth
                label="Texte d'entrée (optionnel)"
                multiline
                rows={3}
                value={inputText}
                onChange={(e) => {
                  setInputText(e.target.value);
                  setConfig({ ...config, input_text: e.target.value });
                }}
                placeholder="Texte qui complétera le prompt de l'agent..."
                helperText="Laissez vide pour utiliser la description du nœud"
                sx={{ mt: 2 }}
              />
            );
          }
        })()}

        {/* Type de rendu */}
        <FormControl fullWidth sx={{ mt: 2 }}>
          <FormLabel>Type de rendu</FormLabel>
          <RadioGroup
            row
            value={outputType}
            onChange={(e) => {
              setOutputType(e.target.value as 'screen' | 'email');
              setConfig({ ...config, output_type: e.target.value });
            }}
          >
            <FormControlLabel value="screen" control={<Radio />} label="À l'écran" />
            <FormControlLabel value="email" control={<Radio />} label="Par email" />
          </RadioGroup>
        </FormControl>

        {/* Configuration email */}
        {outputType === 'email' && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, p: 2, bgcolor: 'action.hover', borderRadius: 1, mt: 2 }}>
            <TextField
              fullWidth
              label="Destinataire"
              type="email"
              value={emailTo}
              onChange={(e) => {
                setEmailTo(e.target.value);
                setConfig({ ...config, email_to: e.target.value });
              }}
              required
            />
            <TextField
              fullWidth
              label="Sujet (optionnel)"
              value={emailSubject}
              onChange={(e) => {
                setEmailSubject(e.target.value);
                setConfig({ ...config, email_subject: e.target.value });
              }}
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Annuler</Button>
        <Button onClick={handleSave} variant="contained">
          {trigger ? "Enregistrer" : "Créer"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
