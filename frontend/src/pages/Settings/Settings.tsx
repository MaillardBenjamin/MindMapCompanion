import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  IconButton,
  InputAdornment,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  Email as EmailIcon,
  SmartToy as AIIcon,
  Search as SearchIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Save as SaveIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { settingsApi, type SettingsResponse, type SettingsUpdate } from '../../services/api';

const Settings = () => {
  const [settings, setSettings] = useState<SettingsResponse>({
    imap_host: '',
    imap_port: 993,
    imap_user: '',
    imap_password: '',
    imap_folder: 'INBOX',
    imap_ssl: true,
    imap_poll_minutes: 2,
    agno_model: 'gpt-5-mini',
    agno_api_key: '',
    openai_api_key: '',
    mistral_api_key: '',
    google_search_api_key: '',
    google_search_engine_id: '',
    bing_search_api_key: '',
    search_provider: 'google',
    agent_langue: 'fr',
    agent_adresse: '',
    agent_prenom: '',
    agent_ton: '',
  });

  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, 'success' | 'error' | null>>({});

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await settingsApi.get();
      setSettings(data);
      setLoading(false);
    } catch (err: any) {
      setError('Erreur lors du chargement des paramètres');
      setLoading(false);
    }
  };

  const handleSave = async (section: string) => {
    setSaving({ ...saving, [section]: true });
    setError(null);
    setSuccess(null);
    
    try {
      let updateData: SettingsUpdate = {};
      
      if (section === 'email') {
        updateData = {
          imap_host: settings.imap_host,
          imap_port: settings.imap_port,
          imap_user: settings.imap_user,
          imap_password: settings.imap_password !== '***' ? settings.imap_password : undefined,
          imap_folder: settings.imap_folder,
          imap_ssl: settings.imap_ssl,
          imap_poll_minutes: settings.imap_poll_minutes,
        };
      } else if (section === 'ai') {
        updateData = {
          agno_model: settings.agno_model,
          agno_api_key: settings.agno_api_key !== '***' ? settings.agno_api_key : undefined,
          openai_api_key: settings.openai_api_key !== '***' ? settings.openai_api_key : undefined,
          mistral_api_key: settings.mistral_api_key !== '***' ? settings.mistral_api_key : undefined,
        };
      } else if (section === 'web_search') {
        updateData = {
          google_search_api_key: settings.google_search_api_key !== '***' ? settings.google_search_api_key : undefined,
          google_search_engine_id: settings.google_search_engine_id,
          bing_search_api_key: settings.bing_search_api_key !== '***' ? settings.bing_search_api_key : undefined,
          search_provider: settings.search_provider,
        };
      } else if (section === 'agents') {
        updateData = {
          agent_langue: settings.agent_langue || 'fr',
          agent_adresse: settings.agent_adresse || undefined,
          agent_prenom: settings.agent_prenom || undefined,
          agent_ton: settings.agent_ton || undefined,
        };
      }

      const result = await settingsApi.update(updateData);
      setSuccess(result.message + (result.note ? ` - ${result.note}` : ''));
      setTimeout(() => setSuccess(null), 5000);
    } catch (err: any) {
      setError(err.detail || 'Erreur lors de la sauvegarde');
    } finally {
      setSaving({ ...saving, [section]: false });
    }
  };

  const handleTest = async (service: string) => {
    try {
      const result = await settingsApi.test(service);
      if (result.status === 'success') {
        setTestResults({ ...testResults, [service]: 'success' });
        setSuccess(result.message);
        setTimeout(() => {
          setTestResults({ ...testResults, [service]: null });
          setSuccess(null);
        }, 3000);
      } else {
        setTestResults({ ...testResults, [service]: 'error' });
        setError(result.message);
      }
    } catch (err: any) {
      setTestResults({ ...testResults, [service]: 'error' });
      setError(err.detail || 'Erreur lors du test');
    }
  };

  const togglePasswordVisibility = (field: string) => {
    setShowPasswords({ ...showPasswords, [field]: !showPasswords[field] });
  };

  const handleFieldChange = (field: keyof SettingsResponse, value: any) => {
    setSettings({ ...settings, [field]: value });
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress sx={{ color: '#00D9FF' }} />
      </Box>
    );
  }

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        p: { xs: 3, md: 5 },
        backgroundColor: '#0A0E17',
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary', mb: 1 }}>
          Paramètres
        </Typography>
        <Typography variant="body1" sx={{ color: 'text.secondary', mb: 4 }}>
          Gérez vos comptes et intégrations
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
            {success}
          </Alert>
        )}

        {/* Email Section */}
        <Card
          sx={{
            backgroundColor: 'rgba(18, 24, 43, 0.6)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '20px',
            mb: 3,
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
              <Box
                sx={{
                  width: 48,
                  height: 48,
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #00D9FF 0%, #0066FF 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <EmailIcon sx={{ color: '#fff', fontSize: 24 }} />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
                  Compte Email (IMAP/SMTP)
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Configuration pour recevoir et envoyer des emails
                </Typography>
              </Box>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={() => handleTest('email')}
                sx={{ color: '#00D9FF', borderColor: '#00D9FF' }}
              >
                Tester
              </Button>
              {testResults.email === 'success' && (
                <Chip icon={<CheckCircleIcon />} label="Connecté" color="success" size="small" />
              )}
              {testResults.email === 'error' && (
                <Chip icon={<ErrorIcon />} label="Erreur" color="error" size="small" />
              )}
            </Box>

            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
              <TextField
                label="Serveur IMAP"
                value={settings.imap_host || ''}
                onChange={(e) => handleFieldChange('imap_host', e.target.value)}
                fullWidth
                size="small"
              />
              <TextField
                label="Port IMAP"
                type="number"
                value={settings.imap_port || 993}
                onChange={(e) => handleFieldChange('imap_port', parseInt(e.target.value) || 993)}
                fullWidth
                size="small"
              />
              <TextField
                label="Utilisateur"
                value={settings.imap_user || ''}
                onChange={(e) => handleFieldChange('imap_user', e.target.value)}
                fullWidth
                size="small"
              />
              <TextField
                label="Mot de passe"
                type={showPasswords.imap_password ? 'text' : 'password'}
                value={settings.imap_password || ''}
                onChange={(e) => handleFieldChange('imap_password', e.target.value)}
                fullWidth
                size="small"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => togglePasswordVisibility('imap_password')} edge="end">
                        {showPasswords.imap_password ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <TextField
                label="Dossier"
                value={settings.imap_folder || ''}
                onChange={(e) => handleFieldChange('imap_folder', e.target.value)}
                fullWidth
                size="small"
              />
              <TextField
                label="Intervalle de vérification (minutes)"
                type="number"
                value={settings.imap_poll_minutes || 2}
                onChange={(e) => handleFieldChange('imap_poll_minutes', parseInt(e.target.value) || 2)}
                fullWidth
                size="small"
              />
            </Box>

            <FormControlLabel
              control={
                <Switch
                  checked={settings.imap_ssl}
                  onChange={(e) => handleFieldChange('imap_ssl', e.target.checked)}
                  sx={{ color: '#00D9FF' }}
                />
              }
              label="Utiliser SSL/TLS"
              sx={{ mt: 2 }}
            />

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={() => handleSave('email')}
                disabled={saving.email}
                sx={{
                  backgroundColor: '#00D9FF',
                  color: '#0A0E17',
                  '&:hover': { backgroundColor: '#00B8D9' },
                }}
              >
                {saving.email ? 'Sauvegarde...' : 'Sauvegarder'}
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* AI Section */}
        <Card
          sx={{
            backgroundColor: 'rgba(18, 24, 43, 0.6)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '20px',
            mb: 3,
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
              <Box
                sx={{
                  width: 48,
                  height: 48,
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #FF6B9D 0%, #FF4081 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <AIIcon sx={{ color: '#fff', fontSize: 24 }} />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
                  Agents IA
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Configuration des clés API pour les agents IA
                </Typography>
              </Box>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={() => handleTest('ai')}
                sx={{ color: '#FF6B9D', borderColor: '#FF6B9D' }}
              >
                Tester
              </Button>
              {testResults.ai === 'success' && (
                <Chip icon={<CheckCircleIcon />} label="OK" color="success" size="small" />
              )}
              {testResults.ai === 'error' && (
                <Chip icon={<ErrorIcon />} label="Erreur" color="error" size="small" />
              )}
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Modèle Agno"
                value={settings.agno_model || ''}
                onChange={(e) => handleFieldChange('agno_model', e.target.value)}
                fullWidth
                size="small"
                helperText="Ex: gpt-4o-mini, gpt-5-mini"
              />
              <TextField
                label="Clé API Agno"
                type={showPasswords.agno_api_key ? 'text' : 'password'}
                value={settings.agno_api_key || ''}
                onChange={(e) => handleFieldChange('agno_api_key', e.target.value)}
                fullWidth
                size="small"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => togglePasswordVisibility('agno_api_key')} edge="end">
                        {showPasswords.agno_api_key ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <TextField
                label="Clé API OpenAI (fallback)"
                type={showPasswords.openai_api_key ? 'text' : 'password'}
                value={settings.openai_api_key || ''}
                onChange={(e) => handleFieldChange('openai_api_key', e.target.value)}
                fullWidth
                size="small"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => togglePasswordVisibility('openai_api_key')} edge="end">
                        {showPasswords.openai_api_key ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <TextField
                label="Clé API Mistral"
                type={showPasswords.mistral_api_key ? 'text' : 'password'}
                value={settings.mistral_api_key || ''}
                onChange={(e) => handleFieldChange('mistral_api_key', e.target.value)}
                fullWidth
                size="small"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => togglePasswordVisibility('mistral_api_key')} edge="end">
                        {showPasswords.mistral_api_key ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={() => handleSave('ai')}
                disabled={saving.ai}
                sx={{
                  backgroundColor: '#FF6B9D',
                  color: '#fff',
                  '&:hover': { backgroundColor: '#FF4081' },
                }}
              >
                {saving.ai ? 'Sauvegarde...' : 'Sauvegarder'}
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Réponses des agents : langue, tutoiement, prénom, ton */}
        <Card
          sx={{
            backgroundColor: 'rgba(18, 24, 43, 0.6)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '20px',
            mb: 3,
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
              <Box
                sx={{
                  width: 48,
                  height: 48,
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <AIIcon sx={{ color: '#fff', fontSize: 24 }} />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
                  Réponses des agents
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Langue, façon de s'adresser à toi, prénom et ton utilisés pour tous les agents
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Langue de réponse</InputLabel>
                <Select
                  value={settings.agent_langue || 'fr'}
                  onChange={(e) => handleFieldChange('agent_langue', e.target.value)}
                  label="Langue de réponse"
                >
                  <MenuItem value="fr">Français</MenuItem>
                  <MenuItem value="en">English</MenuItem>
                  <MenuItem value="es">Español</MenuItem>
                  <MenuItem value="de">Deutsch</MenuItem>
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                  Langue dans laquelle les agents rédigent leurs réponses
                </Typography>
              </FormControl>
              <FormControl fullWidth size="small">
                <InputLabel>Comment s'adresser à moi</InputLabel>
                <Select
                  value={settings.agent_adresse || ''}
                  onChange={(e) => handleFieldChange('agent_adresse', e.target.value)}
                  label="Comment s'adresser à moi"
                >
                  <MenuItem value="">Non spécifié</MenuItem>
                  <MenuItem value="tu">Tutoiement (me dire « tu »)</MenuItem>
                  <MenuItem value="vous">Vouvoiement (me dire « vous »)</MenuItem>
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                  Les agents utiliseront « tu » ou « vous » selon ce choix
                </Typography>
              </FormControl>
              <TextField
                fullWidth
                size="small"
                label="Mon prénom"
                placeholder="Ex. Benjamin"
                value={settings.agent_prenom || ''}
                onChange={(e) => handleFieldChange('agent_prenom', e.target.value)}
                helperText="Pour personnaliser les réponses (ex. « Bonjour Benjamin »)"
              />
              <FormControl fullWidth size="small">
                <InputLabel>Ton / façon de me parler</InputLabel>
                <Select
                  value={settings.agent_ton || ''}
                  onChange={(e) => handleFieldChange('agent_ton', e.target.value)}
                  label="Ton / façon de me parler"
                >
                  <MenuItem value="">Non spécifié</MenuItem>
                  <MenuItem value="formel">Formel</MenuItem>
                  <MenuItem value="amical">Amical</MenuItem>
                  <MenuItem value="neutre">Neutre</MenuItem>
                  <MenuItem value="professionnel">Professionnel</MenuItem>
                  <MenuItem value="bienveillant">Bienveillant</MenuItem>
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                  Style des réponses des agents
                </Typography>
              </FormControl>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={() => handleSave('agents')}
                disabled={saving.agents}
                sx={{
                  backgroundColor: '#8B5CF6',
                  color: '#fff',
                  '&:hover': { backgroundColor: '#6D28D9' },
                }}
              >
                {saving.agents ? 'Sauvegarde...' : 'Sauvegarder'}
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Web Search Section */}
        <Card
          sx={{
            backgroundColor: 'rgba(18, 24, 43, 0.6)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '20px',
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
              <Box
                sx={{
                  width: 48,
                  height: 48,
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <SearchIcon sx={{ color: '#fff', fontSize: 24 }} />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
                  Recherche Web
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Configuration des services de recherche
                </Typography>
              </Box>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={() => handleTest('web_search')}
                sx={{ color: '#10B981', borderColor: '#10B981' }}
              >
                Tester
              </Button>
              {testResults.web_search === 'success' && (
                <Chip icon={<CheckCircleIcon />} label="OK" color="success" size="small" />
              )}
              {testResults.web_search === 'error' && (
                <Chip icon={<ErrorIcon />} label="Erreur" color="error" size="small" />
              )}
            </Box>

            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Fournisseur par défaut</InputLabel>
              <Select
                value={settings.search_provider || 'google'}
                onChange={(e) => handleFieldChange('search_provider', e.target.value)}
                label="Fournisseur par défaut"
                size="small"
              >
                <MenuItem value="google">Google</MenuItem>
                <MenuItem value="bing">Bing</MenuItem>
              </Select>
            </FormControl>

            <Divider sx={{ my: 3 }} />

            <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.primary' }}>
              Google Custom Search
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
              <TextField
                label="Clé API Google"
                type={showPasswords.google_search_api_key ? 'text' : 'password'}
                value={settings.google_search_api_key || ''}
                onChange={(e) => handleFieldChange('google_search_api_key', e.target.value)}
                fullWidth
                size="small"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => togglePasswordVisibility('google_search_api_key')} edge="end">
                        {showPasswords.google_search_api_key ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <TextField
                label="ID du moteur de recherche"
                value={settings.google_search_engine_id || ''}
                onChange={(e) => handleFieldChange('google_search_engine_id', e.target.value)}
                fullWidth
                size="small"
              />
            </Box>

            <Divider sx={{ my: 3 }} />

            <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.primary' }}>
              Bing Search API
            </Typography>
            <TextField
              label="Clé API Bing"
              type={showPasswords.bing_search_api_key ? 'text' : 'password'}
              value={settings.bing_search_api_key || ''}
              onChange={(e) => handleFieldChange('bing_search_api_key', e.target.value)}
              fullWidth
              size="small"
              sx={{ mb: 3 }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => togglePasswordVisibility('bing_search_api_key')} edge="end">
                      {showPasswords.bing_search_api_key ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={() => handleSave('web_search')}
                disabled={saving.web_search}
                sx={{
                  backgroundColor: '#10B981',
                  color: '#fff',
                  '&:hover': { backgroundColor: '#059669' },
                }}
              >
                {saving.web_search ? 'Sauvegarde...' : 'Sauvegarder'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      </motion.div>
    </Box>
  );
};

export default Settings;
