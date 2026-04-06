import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  Divider,
  Button,
} from '@mui/material';
import {
  Bolt as TriggerIcon,
  Settings as ActionIcon,
  AddCircle as NodeIcon,
  Event as EventIcon,
  SmartToy as AgentIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { historyApi, type HistoryItem } from '../../services/api';
// Fonction utilitaire pour formater la date relative
const formatDistanceToNow = (date: Date): string => {
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffInSeconds < 60) {
    return `il y a ${diffInSeconds} seconde${diffInSeconds > 1 ? 's' : ''}`;
  }
  
  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) {
    return `il y a ${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''}`;
  }
  
  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    return `il y a ${diffInHours} heure${diffInHours > 1 ? 's' : ''}`;
  }
  
  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 30) {
    return `il y a ${diffInDays} jour${diffInDays > 1 ? 's' : ''}`;
  }
  
  const diffInMonths = Math.floor(diffInDays / 30);
  if (diffInMonths < 12) {
    return `il y a ${diffInMonths} mois`;
  }
  
  const diffInYears = Math.floor(diffInMonths / 12);
  return `il y a ${diffInYears} an${diffInYears > 1 ? 's' : ''}`;
};

const getTypeIcon = (type: HistoryItem['type']) => {
  switch (type) {
    case 'agent_execution':
      return <AgentIcon sx={{ fontSize: 18 }} />;
    case 'trigger_execution':
      return <TriggerIcon sx={{ fontSize: 18 }} />;
    case 'action_execution':
      return <ActionIcon sx={{ fontSize: 18 }} />;
    case 'node_created':
    case 'node_updated':
      return <NodeIcon sx={{ fontSize: 18 }} />;
    case 'trigger_created':
    case 'trigger_updated':
    case 'trigger_deleted':
      return <TriggerIcon sx={{ fontSize: 18 }} />;
    case 'action_created':
    case 'action_updated':
    case 'action_deleted':
      return <ActionIcon sx={{ fontSize: 18 }} />;
    case 'event':
      return <EventIcon sx={{ fontSize: 18 }} />;
    default:
      return <EventIcon sx={{ fontSize: 18 }} />;
  }
};

const getTypeColor = (type: HistoryItem['type']) => {
  switch (type) {
    case 'agent_execution':
      return '#00D9FF';
    case 'trigger_execution':
      return '#FF6B9D';
    case 'action_execution':
      return '#4ADE80';
    case 'node_created':
      return '#FBBF24';
    case 'node_updated':
      return '#8B5CF6';
    case 'trigger_created':
      return '#FF6B9D';
    case 'trigger_updated':
      return '#FF6B9D';
    case 'trigger_deleted':
      return '#FF5757';
    case 'action_created':
      return '#4ADE80';
    case 'action_updated':
      return '#4ADE80';
    case 'action_deleted':
      return '#FF5757';
    case 'event':
      return '#8B95A8';
    default:
      return '#8B95A8';
  }
};

const getStatusColor = (status?: string | null) => {
  switch (status) {
    case 'success':
      return '#4ADE80';
    case 'failed':
      return '#FF5757';
    case 'pending':
      return '#FBBF24';
    case 'needs_review':
      return '#8B5CF6';
    default:
      return '#8B95A8';
  }
};

/** Au-delà de ce nombre de caractères, la description est repliée par défaut. */
const DESCRIPTION_COLLAPSE_AFTER = 500;

type HistoryEntryCardProps = {
  item: HistoryItem;
};

const HistoryEntryCard = ({ item }: HistoryEntryCardProps) => {
  const [expanded, setExpanded] = useState(false);
  const color = getTypeColor(item.type);
  const statusColor = getStatusColor(item.status);
  const timeAgo = formatDistanceToNow(new Date(item.created_at));
  const desc = (item.description ?? '').trim();
  const isLong = desc.length > DESCRIPTION_COLLAPSE_AFTER;
  const displayDesc =
    expanded || !isLong
      ? desc
      : `${desc.slice(0, DESCRIPTION_COLLAPSE_AFTER).trimEnd()}…`;

  return (
    <Card
      sx={{
        backgroundColor: 'rgba(18, 24, 43, 0.5)',
        border: `1px solid ${color}30`,
        borderRadius: '12px',
        '&:hover': {
          borderColor: `${color}60`,
          backgroundColor: 'rgba(18, 24, 43, 0.7)',
        },
        transition: 'all 0.2s ease',
      }}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
          <Box
            sx={{
              color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minWidth: 32,
              height: 32,
              borderRadius: '8px',
              backgroundColor: `${color}15`,
            }}
          >
            {getTypeIcon(item.type)}
          </Box>

          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 600,
                  color: 'text.primary',
                  flex: 1,
                }}
              >
                {item.title}
              </Typography>
              {item.status && (
                <Chip
                  label={item.status}
                  size="small"
                  sx={{
                    backgroundColor: `${statusColor}20`,
                    color: statusColor,
                    fontSize: '0.65rem',
                    height: 20,
                  }}
                />
              )}
            </Box>

            {desc ? (
              <Box sx={{ mb: isLong ? 0 : 0.5 }}>
                <Typography
                  variant="caption"
                  component="div"
                  sx={{
                    color: 'text.secondary',
                    wordBreak: 'break-word',
                  }}
                >
                  {displayDesc}
                </Typography>
                {isLong && (
                  <Button
                    type="button"
                    variant="text"
                    size="small"
                    aria-expanded={expanded}
                    onClick={() => setExpanded((e) => !e)}
                    sx={{
                      mt: 0.5,
                      p: 0,
                      minWidth: 0,
                      fontSize: '0.75rem',
                      color: '#00D9FF',
                      textTransform: 'none',
                      '&:hover': {
                        backgroundColor: 'rgba(0, 217, 255, 0.08)',
                      },
                    }}
                  >
                    {expanded ? 'Voir moins' : 'Voir plus'}
                  </Button>
                )}
              </Box>
            ) : null}

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mt: 1 }}>
              <Typography
                variant="caption"
                sx={{
                  color: 'text.secondary',
                  fontSize: '0.7rem',
                }}
              >
                {timeAgo}
              </Typography>
              {item.node_label && (
                <>
                  <Divider orientation="vertical" flexItem sx={{ height: 12 }} />
                  <Typography
                    variant="caption"
                    sx={{
                      color: '#00D9FF',
                      fontSize: '0.7rem',
                    }}
                  >
                    Nœud: {item.node_label}
                  </Typography>
                </>
              )}
              {item.agent_name && (
                <>
                  <Divider orientation="vertical" flexItem sx={{ height: 12 }} />
                  <Typography
                    variant="caption"
                    sx={{
                      color: '#FF6B9D',
                      fontSize: '0.7rem',
                    }}
                  >
                    Agent: {item.agent_name}
                  </Typography>
                </>
              )}
            </Box>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

const HistoryPanel = () => {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const limit = 50;

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await historyApi.list(page * limit, limit);
      setItems(response.items);
      setTotal(response.total);
    } catch (err: any) {
      setError(err.detail || 'Erreur lors du chargement de l\'historique');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [page]);

  const handleRefresh = () => {
    setPage(0);
    loadHistory();
  };

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#12182B',
        borderRadius: '16px',
        border: '1px solid rgba(0, 217, 255, 0.2)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 3,
          py: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(0, 217, 255, 0.1)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <EventIcon sx={{ color: '#00D9FF', fontSize: 24 }} />
          <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
            Historique
          </Typography>
          {total > 0 && (
            <Chip
              label={total}
              size="small"
              sx={{
                backgroundColor: 'rgba(0, 217, 255, 0.1)',
                color: '#00D9FF',
                fontSize: '0.75rem',
              }}
            />
          )}
        </Box>
        <Tooltip title="Actualiser">
          <span>
            <IconButton
              onClick={handleRefresh}
              disabled={loading}
              sx={{
                color: '#00D9FF',
                '&:hover': {
                  backgroundColor: 'rgba(0, 217, 255, 0.1)',
                },
              }}
            >
              <RefreshIcon />
            </IconButton>
          </span>
        </Tooltip>
      </Box>

      {/* Content */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          p: 2,
        }}
      >
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress sx={{ color: '#00D9FF' }} />
          </Box>
        ) : items.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <EventIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.5 }} />
            <Typography variant="body1" color="text.secondary">
              Aucun événement dans l'historique
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <AnimatePresence>
              {items.map((item) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                >
                  <HistoryEntryCard item={item} />
                </motion.div>
              ))}
            </AnimatePresence>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default HistoryPanel;
