import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Button,
} from '@mui/material';
import {
  AccountTree as MindmapIcon,
  SmartToy as AgentIcon,
  Refresh as RefreshIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  Add as AddIcon,
  TrendingUp as TrendingUpIcon,
  AccessTime as TimeIcon,
  Bolt as BoltIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { mindmapsApi, historyApi, type MindmapResponse, type HistoryItem } from '../../services/api';
import { useMindmapStore } from '../../stores/mindmapStore';
import { useAuthStore } from '../../stores/authStore';

const Overview = ({ onSelectMindmap }: { onSelectMindmap: (mindmapId: number) => void }) => {
  const [mindmaps, setMindmaps] = useState<MindmapResponse[]>([]);
  const [recentAgentExecutions, setRecentAgentExecutions] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreatingMindmap, setIsCreatingMindmap] = useState(false);
  const { selectMindmap, createMindmap } = useMindmapStore();
  const { user } = useAuthStore();

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const mindmapsData = await mindmapsApi.list();
      setMindmaps(mindmapsData);

      const historyData = await historyApi.list(0, 20);
      const agentExecutions = historyData.items
        .filter((item) => item.type === 'agent_execution')
        .slice(0, 5);
      setRecentAgentExecutions(agentExecutions);
    } catch (err: any) {
      setError(err.detail || 'Erreur lors du chargement des données');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleMindmapClick = async (mindmapId: number) => {
    try {
      await selectMindmap(mindmapId);
      onSelectMindmap(mindmapId);
    } catch (err: any) {
      setError(err.detail || 'Erreur lors du chargement du mindmap');
    }
  };

  const handleCreateMindmap = async () => {
    if (isCreatingMindmap) return;
    setIsCreatingMindmap(true);
    setError(null);

    try {
      const now = new Date();
      const defaultName = `Nouveau mindmap ${now.toLocaleDateString('fr-FR')} ${now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`;
      const created = await createMindmap(defaultName);
      if (created) {
        await loadData();
        onSelectMindmap(created.id);
      }
    } catch (err: any) {
      setError(err?.detail || 'Erreur lors de la création du mindmap');
    } finally {
      setIsCreatingMindmap(false);
    }
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'À l\'instant';
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) return `${diffInMinutes}min`;
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h`;
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays}j`;
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
  };

  const getStatusColor = (status?: string | null) => {
    switch (status) {
      case 'success': return '#10B981';
      case 'failed': return '#EF4444';
      case 'pending': return '#F59E0B';
      default: return '#6B7280';
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Bonjour';
    if (hour < 18) return 'Bon après-midi';
    return 'Bonsoir';
  };

  const successRate = recentAgentExecutions.length > 0
    ? Math.round((recentAgentExecutions.filter(e => e.status === 'success').length / recentAgentExecutions.length) * 100)
    : 0;

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
        backgroundColor: '#0A0E17',
        '&::-webkit-scrollbar': { width: 8 },
        '&::-webkit-scrollbar-track': { background: 'transparent' },
        '&::-webkit-scrollbar-thumb': { background: 'rgba(255,255,255,0.1)', borderRadius: 4 },
      }}
    >
      {/* Hero Section */}
      <Box
        sx={{
          px: { xs: 3, md: 5 },
          pt: { xs: 4, md: 6 },
          pb: 4,
          background: 'linear-gradient(180deg, rgba(0,217,255,0.03) 0%, transparent 100%)',
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
            <Box>
              <Typography
                variant="h3"
                sx={{
                  fontWeight: 700,
                  color: 'text.primary',
                  fontSize: { xs: '1.75rem', md: '2.25rem' },
                  letterSpacing: '-0.02em',
                  mb: 1,
                }}
              >
                {getGreeting()}, {user?.name?.split(' ')[0] || 'vous'} 👋
              </Typography>
              <Typography
                variant="body1"
                sx={{ color: 'text.secondary', fontSize: '1rem', maxWidth: 500 }}
              >
                Voici un aperçu de votre activité et de vos projets
              </Typography>
            </Box>
            <Tooltip title="Actualiser">
              <IconButton
                onClick={loadData}
                sx={{
                  color: 'text.secondary',
                  border: '1px solid rgba(255,255,255,0.1)',
                  '&:hover': { backgroundColor: 'rgba(0, 217, 255, 0.1)', borderColor: '#00D9FF' },
                }}
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </motion.div>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
      </Box>

      {/* Stats Cards */}
      <Box sx={{ px: { xs: 3, md: 5 }, mb: 4 }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' },
            gap: 2,
          }}
        >
          {[
            {
              label: 'Mindmaps',
              value: mindmaps.length,
              icon: <MindmapIcon />,
              color: '#00D9FF',
              gradient: 'linear-gradient(135deg, rgba(0,217,255,0.15) 0%, rgba(0,102,255,0.15) 100%)',
            },
            {
              label: 'Exécutions récentes',
              value: recentAgentExecutions.length,
              icon: <BoltIcon />,
              color: '#FF6B9D',
              gradient: 'linear-gradient(135deg, rgba(255,107,157,0.15) 0%, rgba(255,64,129,0.15) 100%)',
            },
            {
              label: 'Taux de succès',
              value: `${successRate}%`,
              icon: <TrendingUpIcon />,
              color: '#10B981',
              gradient: 'linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(5,150,105,0.15) 100%)',
            },
            {
              label: 'Dernière activité',
              value: recentAgentExecutions[0] ? formatDate(recentAgentExecutions[0].created_at) : '-',
              icon: <TimeIcon />,
              color: '#8B5CF6',
              gradient: 'linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(124,58,237,0.15) 100%)',
            },
          ].map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
            >
              <Card
                sx={{
                  background: stat.gradient,
                  border: `1px solid ${stat.color}20`,
                  borderRadius: '16px',
                  backdropFilter: 'blur(10px)',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    borderColor: `${stat.color}40`,
                    boxShadow: `0 8px 24px ${stat.color}15`,
                  },
                }}
              >
                <CardContent sx={{ p: 2.5 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        {stat.label}
                      </Typography>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: stat.color, mt: 0.5, fontSize: '1.75rem' }}>
                        {stat.value}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: '12px',
                        backgroundColor: `${stat.color}15`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: stat.color,
                      }}
                    >
                      {stat.icon}
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ px: { xs: 3, md: 5 }, pb: 5 }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', lg: '1.5fr 1fr' },
            gap: 3,
          }}
        >
          {/* Mindmaps Section */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card
              sx={{
                backgroundColor: 'rgba(18, 24, 43, 0.6)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '20px',
                backdropFilter: 'blur(10px)',
                height: '100%',
              }}
            >
              <CardContent sx={{ p: 0 }}>
                {/* Header */}
                <Box
                  sx={{
                    px: 3,
                    py: 2.5,
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Box
                      sx={{
                        width: 36,
                        height: 36,
                        borderRadius: '10px',
                        backgroundColor: 'rgba(0, 217, 255, 0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <MindmapIcon sx={{ color: '#00D9FF', fontSize: 20 }} />
                    </Box>
                    <Box>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, color: 'text.primary' }}>
                        Mes Mindmaps
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {mindmaps.length} projet{mindmaps.length > 1 ? 's' : ''}
                      </Typography>
                    </Box>
                  </Box>
                  <Button
                    size="small"
                    startIcon={<AddIcon />}
                    onClick={handleCreateMindmap}
                    disabled={isCreatingMindmap}
                    sx={{
                      color: '#00D9FF',
                      fontSize: '0.8rem',
                      textTransform: 'none',
                      '&:hover': { backgroundColor: 'rgba(0, 217, 255, 0.1)' },
                    }}
                  >
                    Nouveau
                  </Button>
                </Box>

                {/* Content */}
                <Box sx={{ p: 2 }}>
                  {mindmaps.length === 0 ? (
                    <Box sx={{ textAlign: 'center', py: 6 }}>
                      <Box
                        sx={{
                          width: 80,
                          height: 80,
                          borderRadius: '20px',
                          backgroundColor: 'rgba(0, 217, 255, 0.05)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          mx: 'auto',
                          mb: 2,
                        }}
                      >
                        <MindmapIcon sx={{ fontSize: 40, color: '#00D9FF', opacity: 0.5 }} />
                      </Box>
                      <Typography variant="body1" sx={{ color: 'text.secondary', mb: 2 }}>
                        Créez votre premier mindmap
                      </Typography>
                      <Button
                        variant="contained"
                        startIcon={<AddIcon />}
                        onClick={handleCreateMindmap}
                        disabled={isCreatingMindmap}
                        sx={{
                          backgroundColor: '#00D9FF',
                          color: '#0A0E17',
                          textTransform: 'none',
                          fontWeight: 600,
                          '&:hover': { backgroundColor: '#00B8D9' },
                        }}
                      >
                        Commencer
                      </Button>
                    </Box>
                  ) : (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <AnimatePresence>
                        {mindmaps.slice(0, 5).map((mindmap, index) => (
                          <motion.div
                            key={mindmap.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 10 }}
                            transition={{ delay: index * 0.05 }}
                          >
                            <Box
                              onClick={() => handleMindmapClick(mindmap.id)}
                              sx={{
                                p: 2,
                                borderRadius: '12px',
                                backgroundColor: 'rgba(255,255,255,0.02)',
                                border: '1px solid transparent',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 2,
                                transition: 'all 0.2s ease',
                                '&:hover': {
                                  backgroundColor: 'rgba(0, 217, 255, 0.05)',
                                  borderColor: 'rgba(0, 217, 255, 0.2)',
                                  '& .arrow': { opacity: 1, transform: 'translateX(0)' },
                                },
                              }}
                            >
                              <Box
                                sx={{
                                  width: 44,
                                  height: 44,
                                  borderRadius: '10px',
                                  background: 'linear-gradient(135deg, #00D9FF 0%, #0066FF 100%)',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  flexShrink: 0,
                                }}
                              >
                                <MindmapIcon sx={{ color: '#fff', fontSize: 22 }} />
                              </Box>
                              <Box sx={{ flex: 1, minWidth: 0 }}>
                                <Typography
                                  variant="body1"
                                  sx={{
                                    fontWeight: 600,
                                    color: 'text.primary',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {mindmap.name}
                                </Typography>
                                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                  Modifié {formatDate(mindmap.updated_at)}
                                </Typography>
                              </Box>
                              <ArrowForwardIcon
                                className="arrow"
                                sx={{
                                  color: '#00D9FF',
                                  opacity: 0,
                                  transform: 'translateX(-8px)',
                                  transition: 'all 0.2s ease',
                                }}
                              />
                            </Box>
                          </motion.div>
                        ))}
                      </AnimatePresence>
                      {mindmaps.length > 5 && (
                        <Button
                          fullWidth
                          sx={{
                            mt: 1,
                            color: 'text.secondary',
                            textTransform: 'none',
                            '&:hover': { backgroundColor: 'rgba(255,255,255,0.05)' },
                          }}
                        >
                          Voir les {mindmaps.length - 5} autres →
                        </Button>
                      )}
                    </Box>
                  )}
                </Box>
              </CardContent>
            </Card>
          </motion.div>

          {/* Activity Timeline */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card
              sx={{
                backgroundColor: 'rgba(18, 24, 43, 0.6)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '20px',
                backdropFilter: 'blur(10px)',
                height: '100%',
              }}
            >
              <CardContent sx={{ p: 0 }}>
                {/* Header */}
                <Box
                  sx={{
                    px: 3,
                    py: 2.5,
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Box
                      sx={{
                        width: 36,
                        height: 36,
                        borderRadius: '10px',
                        backgroundColor: 'rgba(255, 107, 157, 0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <AgentIcon sx={{ color: '#FF6B9D', fontSize: 20 }} />
                    </Box>
                    <Box>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, color: 'text.primary' }}>
                        Activité récente
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        Dernières exécutions d'agents
                      </Typography>
                    </Box>
                  </Box>
                </Box>

                {/* Content */}
                <Box sx={{ p: 2 }}>
                  {recentAgentExecutions.length === 0 ? (
                    <Box sx={{ textAlign: 'center', py: 6 }}>
                      <Box
                        sx={{
                          width: 80,
                          height: 80,
                          borderRadius: '20px',
                          backgroundColor: 'rgba(255, 107, 157, 0.05)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          mx: 'auto',
                          mb: 2,
                        }}
                      >
                        <AgentIcon sx={{ fontSize: 40, color: '#FF6B9D', opacity: 0.5 }} />
                      </Box>
                      <Typography variant="body1" sx={{ color: 'text.secondary' }}>
                        Aucune activité récente
                      </Typography>
                    </Box>
                  ) : (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <AnimatePresence>
                        {recentAgentExecutions.map((execution, index) => (
                          <motion.div
                            key={execution.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ delay: index * 0.05 }}
                          >
                            <Box
                              sx={{
                                p: 2,
                                borderRadius: '12px',
                                backgroundColor: 'rgba(255,255,255,0.02)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 2,
                                position: 'relative',
                                transition: 'all 0.2s ease',
                                '&:hover': {
                                  backgroundColor: 'rgba(255, 107, 157, 0.05)',
                                },
                              }}
                            >
                              {/* Timeline dot */}
                              <Box
                                sx={{
                                  width: 12,
                                  height: 12,
                                  borderRadius: '50%',
                                  backgroundColor: getStatusColor(execution.status),
                                  boxShadow: `0 0 8px ${getStatusColor(execution.status)}60`,
                                  flexShrink: 0,
                                }}
                              />
                              <Box sx={{ flex: 1, minWidth: 0 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                  <Typography
                                    variant="body2"
                                    sx={{
                                      fontWeight: 600,
                                      color: 'text.primary',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      whiteSpace: 'nowrap',
                                    }}
                                  >
                                    {execution.agent_name || 'Agent'}
                                  </Typography>
                                  <Chip
                                    size="small"
                                    label={execution.status}
                                    sx={{
                                      height: 20,
                                      fontSize: '0.65rem',
                                      backgroundColor: `${getStatusColor(execution.status)}15`,
                                      color: getStatusColor(execution.status),
                                      fontWeight: 600,
                                    }}
                                  />
                                </Box>
                                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                  {formatDate(execution.created_at)}
                                </Typography>
                              </Box>
                              {execution.status === 'success' && (
                                <SuccessIcon sx={{ color: '#10B981', fontSize: 18 }} />
                              )}
                              {execution.status === 'failed' && (
                                <ErrorIcon sx={{ color: '#EF4444', fontSize: 18 }} />
                              )}
                              {execution.status === 'pending' && (
                                <PendingIcon sx={{ color: '#F59E0B', fontSize: 18 }} />
                              )}
                            </Box>
                          </motion.div>
                        ))}
                      </AnimatePresence>
                    </Box>
                  )}
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Box>
      </Box>
    </Box>
  );
};

export default Overview;
