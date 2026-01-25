import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  TextField,
  Typography,
  IconButton,
  Switch,
  FormControlLabel,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  approveProposal,
  getNode,
  listActions,
  listProposals,
  listTriggers,
  rejectProposal,
  updateNode,
  createTrigger,
  updateTrigger,
  deleteTrigger,
  executeTrigger,
} from "../../api/client";
import TriggerForm from "../../components/Trigger/TriggerForm";
import { useMindmapStore } from "../../stores/mindmapStore";
import { STATUS_ORDER, getStatusColor, getStatusLabel } from "../../utils/nodeStatus";
import type { NodeStatus } from "../../../../shared/types";
import { useNotification } from "../../hooks/useNotification";

type NodeDrawerProps = {
  open: boolean;
  nodeId: string | null;
  onClose: () => void;
  onUpdated: () => void;
};

export default function NodeDrawer({ open, nodeId, onClose, onUpdated }: NodeDrawerProps) {
  const [node, setNode] = useState<any>(null);
  const [proposals, setProposals] = useState<any[]>([]);
  const [triggers, setTriggers] = useState<any[]>([]);
  const [actions, setActions] = useState<any[]>([]);
  const [tags, setTags] = useState("");
  const [status, setStatus] = useState("");
  const [nextAction, setNextAction] = useState("");
  const [triggerFormOpen, setTriggerFormOpen] = useState(false);
  const [editingTrigger, setEditingTrigger] = useState<any>(null);
  const { showSuccess, showError, showWarning } = useNotification();

  const loadNodeDetails = async () => {
    console.log("[NodeDrawer] loadNodeDetails appelé pour nodeId:", nodeId);
    if (!nodeId) {
      console.log("[NodeDrawer] Pas de nodeId, arrêt");
      return;
    }
    try {
      const data = await getNode(nodeId);
      console.log("[NodeDrawer] Node data reçu:", data);
      setNode(data);
      setTags((data.tags || []).join(", ") || "");
      setStatus(data.status || "");
      setNextAction(data.next_action || "");
      
      const pending = await listProposals("pending", nodeId);
      setProposals(pending.proposals || []);
      
      const t = await listTriggers(nodeId);
      console.log("[NodeDrawer] Triggers reçus de l'API:", t.triggers);
      console.log("[NodeDrawer] Nombre de triggers reçus:", t.triggers?.length || 0);
      console.log("[NodeDrawer] Triggers actuels dans l'état avant setTriggers:", triggers);
      
      const newTriggers = t.triggers || [];
      console.log("[NodeDrawer] Appel de setTriggers avec:", newTriggers);
      setTriggers(newTriggers);
      console.log("[NodeDrawer] setTriggers appelé");
      
      const a = await listActions(nodeId);
      setActions(a.actions || []);
      console.log("[NodeDrawer] loadNodeDetails terminé - triggers:", newTriggers.length);
    } catch (error) {
      console.error("[NodeDrawer] Erreur dans loadNodeDetails:", error);
    }
  };

  useEffect(() => {
    console.log("[NodeDrawer] useEffect principal - nodeId changé:", nodeId);
    loadNodeDetails();
  }, [nodeId]);
  
  // Log quand triggers change
  useEffect(() => {
    console.log("[NodeDrawer] État triggers a changé - nouveau nombre:", triggers.length);
    console.log("[NodeDrawer] Triggers actuels:", triggers);
  }, [triggers]);

  const handleSave = async () => {
    if (!nodeId) return;
    try {
      const payload: Record<string, unknown> = {
        status: status || undefined,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        next_action: nextAction || undefined,
      };
      await updateNode(nodeId, payload);
      await loadNodeDetails();
      onUpdated();
      showSuccess("Nœud mis à jour avec succès");
    } catch (error) {
      console.error("Erreur lors de la sauvegarde:", error);
      showError("Erreur lors de la mise à jour du nœud");
    }
  };

  const handleApprove = async (proposalId: string) => {
    try {
      await approveProposal(proposalId);
      await loadNodeDetails();
      onUpdated();
      showSuccess("Proposal approuvée et appliquée");
    } catch (error) {
      console.error("Erreur lors de l'approbation:", error);
      showError("Erreur lors de l'approbation de la proposal");
    }
  };

  const handleReject = async (proposalId: string) => {
    try {
      await rejectProposal(proposalId);
      await loadNodeDetails();
      onUpdated();
      showSuccess("Proposal rejetée");
    } catch (error) {
      console.error("Erreur lors du rejet:", error);
      showError("Erreur lors du rejet de la proposal");
    }
  };

  const handleCreateTrigger = () => {
    console.log("[NodeDrawer] handleCreateTrigger appelé");
    setEditingTrigger(null);
    setTriggerFormOpen(true);
  };

  const handleEditTrigger = (trigger: any) => {
    setEditingTrigger(trigger);
    setTriggerFormOpen(true);
  };

  const handleDeleteTrigger = async (triggerId: string) => {
    console.log("[NodeDrawer] handleDeleteTrigger appelé pour:", triggerId);
    console.log("[NodeDrawer] Triggers actuels avant suppression:", triggers);
    if (confirm("Êtes-vous sûr de vouloir supprimer ce trigger ?")) {
      try {
        console.log("[NodeDrawer] Suppression du trigger:", triggerId);
        // Mettre à jour immédiatement l'état local AVANT l'appel API
        const newTriggers = triggers.filter((t) => String(t.id) !== String(triggerId));
        console.log("[NodeDrawer] Nouveaux triggers après filtre:", newTriggers);
        setTriggers(newTriggers);
        console.log("[NodeDrawer] État local mis à jour, appel API...");
        
        // Supprimer directement via l'API
        await deleteTrigger(triggerId);
        console.log("[NodeDrawer] Trigger supprimé sur le serveur, rechargement des données...");
        
        // Recharger depuis le serveur pour être sûr
        await loadNodeDetails();
        console.log("[NodeDrawer] Données rechargées");
        onUpdated();
        console.log("[NodeDrawer] Suppression terminée");
        showSuccess("Trigger supprimé avec succès");
      } catch (error) {
        console.error("[NodeDrawer] Erreur lors de la suppression:", error);
        showError("Erreur lors de la suppression du trigger");
        // Recharger en cas d'erreur
        await loadNodeDetails();
      }
    }
  };

  const handleToggleTrigger = async (trigger: any) => {
    try {
      await updateTrigger(trigger.id, { enabled: !trigger.enabled });
      await loadNodeDetails();
      onUpdated();
      showSuccess(trigger.enabled ? "Trigger désactivé" : "Trigger activé");
    } catch (error) {
      console.error("Erreur lors de la mise à jour:", error);
      showError("Erreur lors de la mise à jour du trigger");
    }
  };

  const handleExecuteTrigger = async (trigger: any) => {
    if (!trigger.enabled) {
      alert("Le trigger est désactivé. Activez-le d'abord.");
      return;
    }

    // Pour l'instant, on exécute avec une action par défaut
    // TODO: Permettre de sélectionner l'action/agent à exécuter
    try {
      // Récupérer la première action du node
      const nodeActions = await listActions(nodeId!);
      if (nodeActions.actions && nodeActions.actions.length > 0) {
        const firstAction = nodeActions.actions[0];
        await executeTrigger(trigger.id, {
          task_type: "action",
          task_id: firstAction.id,
          output_type: "screen",
        });
        showSuccess("Trigger exécuté avec succès");
        await loadNodeDetails();
      } else {
        showWarning("Aucune action associée à ce node. Créez d'abord une action.");
      }
    } catch (error) {
      console.error("Erreur lors de l'exécution:", error);
      showError("Erreur lors de l'exécution du trigger");
    }
  };

  const handleTriggerSaved = async (newTrigger?: any) => {
    console.log("[NodeDrawer] handleTriggerSaved appelé avec:", newTrigger);
    console.log("[NodeDrawer] Rechargement des détails du node...");
    try {
      // Toujours recharger depuis le serveur pour avoir les données à jour
      await loadNodeDetails();
      console.log("[NodeDrawer] Appel de onUpdated()");
      onUpdated();
      console.log("[NodeDrawer] handleTriggerSaved terminé");
      showSuccess(newTrigger ? "Trigger créé avec succès" : "Trigger mis à jour avec succès");
    } catch (error) {
      console.error("Erreur lors de la sauvegarde du trigger:", error);
      showError("Erreur lors de la sauvegarde du trigger");
    }
  };

  const getTriggerTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      email_received: "Email reçu",
      date_reached: "Date atteinte",
      cron: "Cron",
      state_changed: "Changement d'état",
      manual: "Manuel",
    };
    return labels[type] || type;
  };

  return (
    <>
      <Drawer anchor="right" open={open} onClose={onClose}>
        <Box sx={{ width: 360, p: 2 }}>
          <Typography variant="h6">Node</Typography>
          {node ? (
            <>
              <Typography variant="body2" sx={{ mt: 1 }}>
                {node.raw_text}
              </Typography>
              <FormControl fullWidth sx={{ mt: 2 }}>
                <InputLabel>Statut</InputLabel>
                <Select
                  value={status || 'inbox'}
                  label="Statut"
                  onChange={(e) => setStatus(e.target.value)}
                  sx={{
                    '& .MuiSelect-select': {
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                    },
                  }}
                >
                  {STATUS_ORDER.map((s) => (
                    <MenuItem
                      key={s}
                      value={s}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        '&:hover': {
                          backgroundColor: `${getStatusColor(s)}20`,
                        },
                        '&.Mui-selected': {
                          backgroundColor: `${getStatusColor(s)}30`,
                          '&:hover': {
                            backgroundColor: `${getStatusColor(s)}40`,
                          },
                        },
                      }}
                    >
                      <Box
                        sx={{
                          width: 10,
                          height: 10,
                          borderRadius: '50%',
                          backgroundColor: getStatusColor(s),
                          boxShadow: `0 0 6px ${getStatusColor(s)}80`,
                          flexShrink: 0,
                        }}
                      />
                      {getStatusLabel(s)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                fullWidth
                label="Tags (comma)"
                value={tags || ''}
                onChange={(e) => setTags(e.target.value)}
                sx={{ mt: 2 }}
              />
              <TextField
                fullWidth
                label="Next action"
                value={nextAction || ''}
                onChange={(e) => setNextAction(e.target.value)}
                sx={{ mt: 2 }}
              />
              <Button variant="contained" onClick={handleSave} sx={{ mt: 2 }}>
                Sauvegarder
              </Button>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1">Proposals</Typography>
              {proposals.map((proposal) => (
                <Box key={proposal.id} sx={{ mt: 1 }}>
                  <Typography variant="body2">
                    {proposal.proposal_json?.title}
                  </Typography>
                  <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
                    <Button size="small" variant="outlined" onClick={() => handleApprove(proposal.id)}>
                      Approve
                    </Button>
                    <Button size="small" variant="text" onClick={() => handleReject(proposal.id)}>
                      Reject
                    </Button>
                  </Box>
                </Box>
              ))}
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Typography variant="subtitle1">Triggers</Typography>
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={handleCreateTrigger}
                  variant="outlined"
                >
                  Ajouter
                </Button>
              </Box>
              {(() => {
                console.log("[NodeDrawer] RENDER - Nombre de triggers à afficher:", triggers.length);
                console.log("[NodeDrawer] RENDER - Triggers:", triggers);
                return null;
              })()}
              {triggers.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Aucun trigger configuré
                </Typography>
              ) : (
                triggers.map((trigger) => (
                  <Card key={trigger.id} sx={{ mt: 1 }}>
                    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle2">
                            {getTriggerTypeLabel(trigger.trigger_type)}
                          </Typography>
                          {trigger.config && Object.keys(trigger.config).length > 0 && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                              {trigger.trigger_type === "date_reached" && trigger.config.run_at && (
                                <>Date: {new Date(trigger.config.run_at).toLocaleString("fr-FR")}</>
                              )}
                              {trigger.trigger_type === "cron" && trigger.config.cron_expression && (
                                <>Cron: {trigger.config.cron_expression}</>
                              )}
                              {trigger.trigger_type === "state_changed" && (
                                <>
                                  {trigger.config.from_status} → {trigger.config.to_status}
                                </>
                              )}
                            </Typography>
                          )}
                          {trigger.last_fired_at && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                              Dernière exécution: {new Date(trigger.last_fired_at).toLocaleString("fr-FR")}
                            </Typography>
                          )}
                        </Box>
                        <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                          <FormControlLabel
                            control={
                              <Switch
                                size="small"
                                checked={trigger.enabled}
                                onChange={() => handleToggleTrigger(trigger)}
                              />
                            }
                            label=""
                            sx={{ m: 0 }}
                          />
                          <IconButton
                            size="small"
                            onClick={() => handleExecuteTrigger(trigger)}
                            title="Lancer le trigger"
                            color="primary"
                          >
                            <PlayArrowIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleEditTrigger(trigger)}
                            title="Modifier"
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => {
                              console.log("[NodeDrawer] Clic sur supprimer - trigger.id:", trigger.id, "type:", typeof trigger.id);
                              handleDeleteTrigger(String(trigger.id));
                            }}
                            title="Supprimer"
                            color="error"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      </Box>
                      {/* Afficher les actions associées */}
                      {actions.length > 0 && (
                        <Box sx={{ mt: 1, pt: 1, borderTop: "1px solid", borderColor: "divider" }}>
                          <Typography variant="caption" color="text.secondary">
                            Actions associées: {actions.map((a) => a.action_type).join(", ")}
                          </Typography>
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1">Actions</Typography>
              {actions.map((action) => (
                <Chip key={action.id} label={action.action_type} sx={{ mr: 1, mt: 1 }} />
              ))}
            </>
          ) : (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Sélectionne un node.
            </Typography>
          )}
        </Box>
      </Drawer>
      {nodeId && (
        <TriggerForm
          open={triggerFormOpen}
          nodeId={nodeId}
          trigger={editingTrigger}
          onClose={() => {
            setTriggerFormOpen(false);
            setEditingTrigger(null);
          }}
          onSave={handleTriggerSaved}
        />
      )}
    </>
  );
}
