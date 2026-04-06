import { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Chip,
  IconButton,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import CloseIcon from "@mui/icons-material/Close";
import { listConfigurableAgents, executeConfigurableAgent, loadAgentsFromFiles } from "../../api/client";

export default function AgentsList() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [executing, setExecuting] = useState<Record<number, boolean>>({});
  const [loadingFromFiles, setLoadingFromFiles] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error" | "warning";
  }>({
    open: false,
    message: "",
    severity: "success",
  });
  /** Détails du dernier « Charger depuis fichiers » (erreurs visibles tant que l'utilisateur ne ferme pas) */
  const [loadFromFilesReport, setLoadFromFilesReport] = useState<{ summary: string; errors: string[] } | null>(null);
  const [executeDialog, setExecuteDialog] = useState<{ open: boolean; agent: any | null }>({
    open: false,
    agent: null,
  });
  const [executeForm, setExecuteForm] = useState<Record<string, string>>({});

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listConfigurableAgents();
      setAgents(data.agents || []);
    } catch (err: any) {
      setError(err.message || "Erreur lors du chargement des agents");
      console.error("Erreur:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async (agent: any) => {
    // Si l'agent a un input_schema, ouvrir un formulaire structuré
    if (agent.input_schema && Object.keys(agent.input_schema).length > 0) {
      // Initialiser le formulaire avec des valeurs vides pour tous les champs du schéma
      const initialForm: Record<string, string> = {};
      Object.keys(agent.input_schema).forEach((key) => {
        initialForm[key] = "";
      });
      setExecuteForm(initialForm);
      setExecuteDialog({ open: true, agent });
      return;
    }
    
    // Sinon, utiliser le prompt simple
    const inputText = prompt(`Entrez le texte d'entrée pour "${agent.name}":`);
    if (!inputText) return;

    try {
      setExecuting({ ...executing, [agent.id]: true });
      const result = await executeConfigurableAgent(agent.id, inputText);
      
      // Afficher le résultat
      if (result.output_parsed) {
        alert(`Résultat:\n${JSON.stringify(result.output_parsed, null, 2)}`);
      } else if (result.output_raw) {
        alert(`Résultat:\n${result.output_raw}`);
      } else {
        alert("Exécution réussie !");
      }
    } catch (err: any) {
      alert(`Erreur: ${err.message || "Erreur lors de l'exécution"}`);
      console.error("Erreur:", err);
    } finally {
      setExecuting({ ...executing, [agent.id]: false });
    }
  };

  const handleExecuteWithForm = async () => {
    if (!executeDialog.agent) return;
    
    const agent = executeDialog.agent;
    
    // Construire le texte d'entrée (input_text si présent, sinon construire depuis les autres champs)
    const inputText = executeForm.input_text || 
      (agent.input_schema 
        ? Object.entries(agent.input_schema)
            .filter(([key]) => key !== "input_text")
            .map(([key]) => executeForm[key])
            .filter(Boolean)
            .join(", ")
        : "");
    
    // Passer tous les champs sauf input_text comme options
    const options: Record<string, any> = {};
    Object.keys(executeForm).forEach((key) => {
      if (key !== "input_text" && executeForm[key]) {
        options[key] = executeForm[key];
      }
    });

    try {
      setExecuting({ ...executing, [agent.id]: true });
      setExecuteDialog({ open: false, agent: null });
      
      const result = await executeConfigurableAgent(agent.id, inputText, options);
      
      // Afficher le résultat
      if (result.output_parsed) {
        alert(`Résultat:\n${JSON.stringify(result.output_parsed, null, 2)}`);
      } else if (result.output_raw) {
        alert(`Résultat:\n${result.output_raw}`);
      } else {
        alert("Exécution réussie !");
      }
    } catch (err: any) {
      alert(`Erreur: ${err.message || "Erreur lors de l'exécution"}`);
      console.error("Erreur:", err);
    } finally {
      setExecuting({ ...executing, [agent.id]: false });
    }
  };

  const handleLoadFromFiles = async () => {
    try {
      setLoadingFromFiles(true);
      console.log('[AgentsList] Chargement des agents depuis les fichiers...');
      const result = await loadAgentsFromFiles();
      console.log('[AgentsList] Résultat du chargement:', result);
      
      let message = `${result.loaded} agent(s) chargé(s) depuis les fichiers`;
      if (result.errors && result.errors.length > 0) {
        console.error('[AgentsList] Erreurs lors du chargement:', result.errors);
      }
      if (result.agents && result.agents.length > 0) {
        console.log('[AgentsList] Agents chargés:', result.agents);
        const created = result.agents.filter((a: { status?: string }) => a.status === "créé").length;
        const updated = result.agents.filter((a: { status?: string }) => a.status === "mis à jour").length;
        message = `${created} créé(s), ${updated} mis à jour`;
      }

      const errs = Array.isArray(result.errors) ? result.errors : [];
      if (errs.length > 0) {
        setLoadFromFilesReport({ summary: message, errors: errs });
      } else {
        setLoadFromFilesReport(null);
      }

      setSnackbar({
        open: true,
        message: errs.length > 0 ? `${message} — détail ci-dessous` : message,
        severity: result.loaded > 0 ? "success" : errs.length > 0 ? "error" : "warning",
      });
      // Recharger la liste des agents
      await loadAgents();
    } catch (err: any) {
      console.error('[AgentsList] Erreur lors du chargement:', err);
      setSnackbar({
        open: true,
        message: `Erreur: ${err.message || "Erreur lors du chargement"}`,
        severity: "error",
      });
    } finally {
      setLoadingFromFiles(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">{error}</Alert>
        <Button onClick={loadAgents} sx={{ mt: 2 }}>
          Réessayer
        </Button>
      </Box>
    );
  }

  if (agents.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        {loadFromFilesReport && loadFromFilesReport.errors.length > 0 && (
          <Alert
            severity="error"
            onClose={() => setLoadFromFilesReport(null)}
            sx={{ mb: 2, textAlign: "left", maxWidth: 720, mx: "auto" }}
          >
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {loadFromFilesReport.summary}
            </Typography>
            <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
              {loadFromFilesReport.errors.map((e, i) => (
                <Typography key={i} component="li" variant="body2">
                  {e}
                </Typography>
              ))}
            </Box>
          </Alert>
        )}
        <Typography variant="h6" sx={{ mb: 2 }}>
          Aucun agent configuré
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Les agents configurables apparaîtront ici une fois créés.
          <br />
          Cliquez sur "Charger depuis fichiers" pour charger les agents depuis les fichiers .md dans backend/app/agent_configs/agents/
        </Typography>
        <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
          <Button
            onClick={handleLoadFromFiles}
            variant="contained"
            startIcon={loadingFromFiles ? <CircularProgress size={16} /> : <RefreshIcon />}
            disabled={loadingFromFiles}
          >
            Charger depuis fichiers
          </Button>
          <Button onClick={loadAgents} variant="outlined">
            Actualiser
          </Button>
        </Box>
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          message={snackbar.message}
        />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {loadFromFilesReport && loadFromFilesReport.errors.length > 0 && (
        <Alert
          severity="warning"
          onClose={() => setLoadFromFilesReport(null)}
          sx={{ mb: 2 }}
        >
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {loadFromFilesReport.summary}
          </Typography>
          <Typography variant="caption" display="block" sx={{ mb: 1 }}>
            Certaines fiches .md n&apos;ont pas pu être importées :
          </Typography>
          <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
            {loadFromFilesReport.errors.map((e, i) => (
              <Typography key={i} component="li" variant="body2">
                {e}
              </Typography>
            ))}
          </Box>
        </Alert>
      )}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h6">Agents configurables</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            onClick={handleLoadFromFiles}
            size="small"
            variant="outlined"
            startIcon={loadingFromFiles ? <CircularProgress size={16} /> : <RefreshIcon />}
            disabled={loadingFromFiles}
          >
            Charger depuis fichiers
          </Button>
          <Button onClick={loadAgents} size="small" variant="outlined">
            Actualiser
          </Button>
        </Box>
      </Box>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {agents.map((agent) => (
          <Card key={agent.id}>
            <CardContent>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6">{agent.name}</Typography>
                  {agent.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      {agent.description}
                    </Typography>
                  )}
                  <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap" }}>
                    <Chip
                      label={agent.is_active ? "Actif" : "Inactif"}
                      color={agent.is_active ? "success" : "default"}
                      size="small"
                    />
                    {agent.is_public && (
                      <Chip label="Public" color="primary" size="small" />
                    )}
                    {agent.tools && agent.tools.length > 0 && (
                      <Chip
                        label={`${agent.tools.length} outil(s)`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </Box>
                <IconButton
                  onClick={() => handleExecute(agent)}
                  disabled={executing[agent.id] || !agent.is_active}
                  color="primary"
                  title="Exécuter l'agent"
                >
                  {executing[agent.id] ? (
                    <CircularProgress size={24} />
                  ) : (
                    <PlayArrowIcon />
                  )}
                </IconButton>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
      
      {/* Dialog pour l'exécution avec formulaire dynamique */}
      <Dialog
        open={executeDialog.open}
        onClose={() => setExecuteDialog({ open: false, agent: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle
          sx={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 1,
            pr: 1,
          }}
        >
          <Box sx={{ flex: 1, minWidth: 0, pt: 0.25 }}>
            Exécuter {executeDialog.agent?.name || "l'agent"}
          </Box>
          <IconButton
            aria-label="Fermer la fenêtre"
            onClick={() => setExecuteDialog({ open: false, agent: null })}
            edge="end"
            size="small"
            sx={{ color: "text.secondary", flexShrink: 0, mt: -0.25 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}>
            {executeDialog.agent?.input_schema &&
              Object.entries(executeDialog.agent.input_schema).map(([key, field]: [string, any]) => {
                const fieldValue = executeForm[key] || "";
                const isRequired = field.required === true;

                if (field.type === "select") {
                  return (
                    <FormControl key={key} fullWidth required={isRequired}>
                      <InputLabel>{field.label}</InputLabel>
                      <Select
                        value={fieldValue}
                        onChange={(e) => setExecuteForm({ ...executeForm, [key]: e.target.value })}
                        label={field.label}
                      >
                        {field.options?.map((option: any) => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </Select>
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
                      onChange={(e) => setExecuteForm({ ...executeForm, [key]: e.target.value })}
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
                    onChange={(e) => setExecuteForm({ ...executeForm, [key]: e.target.value })}
                    fullWidth
                    required={isRequired}
                    helperText={field.description}
                  />
                );
              })}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExecuteDialog({ open: false, agent: null })}>
            Annuler
          </Button>
          <Button
            onClick={handleExecuteWithForm}
            variant="contained"
            disabled={
              executeDialog.agent?.input_schema
                ? Object.entries(executeDialog.agent.input_schema).some(
                    ([key, field]: [string, any]) => field.required && !executeForm[key]
                  )
                : false
            }
          >
            Exécuter
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
