import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Box, Typography, IconButton, Tooltip, Badge } from '@mui/material';
import {
  BoltOutlined as TriggerIcon,
  Inbox as InboxIcon,
  HelpOutline as ClarifyIcon,
  PlayArrow as ReadyIcon,
  Loop as DoingIcon,
  HourglassEmpty as WaitingIcon,
  CheckCircle as DoneIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import type { MindmapNodeData } from '../../stores/mindmapStore';
import { getStatusColor, getStatusLabel } from '../../utils/nodeStatus';
import type { NodeStatus } from '../../../../shared/types';

// Style commun pour les handles
const handleStyle = (color: string) => ({
  width: 8,
  height: 8,
  background: color,
  border: 'none',
  boxShadow: `0 0 10px ${color}`,
});

const MindmapNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as MindmapNodeData & { showIds?: boolean };
  const { label, description = '', isRoot, triggers = [], status = 'inbox' as NodeStatus, showIds = false, backendId } = nodeData;

  // La couleur du nœud est basée sur son statut
  const nodeColor = getStatusColor(status);

  // Tronquer la description pour l'affichage (max 60 caractères)
  const truncatedDescription = description.length > 60 
    ? `${description.substring(0, 60)}...` 
    : description;

  const getStatusIcon = () => {
    const iconSx = { fontSize: 14, color: nodeColor };
    switch (status) {
      case 'inbox':
        return <InboxIcon sx={iconSx} />;
      case 'clarify':
        return <ClarifyIcon sx={iconSx} />;
      case 'ready':
        return <ReadyIcon sx={iconSx} />;
      case 'doing':
        return (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          >
            <DoingIcon sx={iconSx} />
          </motion.div>
        );
      case 'waiting':
        return (
          <motion.div
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <WaitingIcon sx={iconSx} />
          </motion.div>
        );
      case 'done':
        return <DoneIcon sx={iconSx} />;
      default:
        return null;
    }
  };

  return (
    <motion.div
      initial={false}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      <Box
        sx={{
          position: 'relative',
          minWidth: isRoot ? 140 : 100,
          maxWidth: 180,
        }}
      >
        {/* Handles à gauche - pour les nœuds à droite de leur parent */}
        <Handle
          type="target"
          position={Position.Left}
          id="target-left"
          style={handleStyle(nodeColor)}
        />
        <Handle
          type="source"
          position={Position.Left}
          id="source-left"
          style={handleStyle(nodeColor)}
        />

        {/* Handles à droite - pour les nœuds à gauche de leur parent */}
        <Handle
          type="target"
          position={Position.Right}
          id="target-right"
          style={handleStyle(nodeColor)}
        />
        <Handle
          type="source"
          position={Position.Right}
          id="source-right"
          style={handleStyle(nodeColor)}
        />

        <Box
          sx={{
            px: isRoot ? 3 : 2,
            py: isRoot ? 2 : 1.5,
            borderRadius: isRoot ? '20px' : '12px',
            backgroundColor: isRoot ? nodeColor : `rgba(18, 24, 43, 0.95)`,
            border: `2px solid ${selected ? '#fff' : nodeColor}`,
            boxShadow: selected
              ? `0 0 30px ${nodeColor}80, 0 8px 32px rgba(0, 0, 0, 0.3)`
              : `0 4px 20px rgba(0, 0, 0, 0.3)`,
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            '&:hover': {
              transform: 'scale(1.05)',
              boxShadow: `0 0 30px ${nodeColor}60, 0 12px 40px rgba(0, 0, 0, 0.4)`,
            },
          }}
        >
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {showIds && backendId !== undefined && (
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.6rem',
                  color: isRoot ? 'rgba(10, 14, 23, 0.6)' : 'rgba(232, 237, 245, 0.5)',
                  fontFamily: 'monospace',
                  textAlign: 'center',
                  lineHeight: 1,
                  mb: -0.5,
                }}
              >
                ID: {backendId}
                {nodeData.backendParentId !== undefined && nodeData.backendParentId !== null && (
                  <span style={{ marginLeft: '4px', opacity: 0.7 }}>
                    (P:{nodeData.backendParentId})
                  </span>
                )}
              </Typography>
            )}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {getStatusIcon()}
              <Typography
                variant={isRoot ? 'subtitle1' : 'body2'}
                sx={{
                  fontWeight: isRoot ? 700 : 500,
                  color: isRoot ? '#0A0E17' : '#E8EDF5',
                  textAlign: 'center',
                  wordBreak: 'break-word',
                  lineHeight: 1.2,
                }}
              >
                {label}
              </Typography>
            </Box>
            {truncatedDescription && (
              <Typography
                variant="caption"
                sx={{
                  color: isRoot ? 'rgba(10, 14, 23, 0.7)' : 'rgba(232, 237, 245, 0.7)',
                  fontSize: isRoot ? '0.75rem' : '0.65rem',
                  lineHeight: 1.3,
                  wordBreak: 'break-word',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {truncatedDescription}
              </Typography>
            )}
          </Box>

          {triggers.length > 0 && (
            <Tooltip title={`${triggers.length} trigger(s) configuré(s)`}>
              <Badge
                badgeContent={triggers.length}
                color="secondary"
                sx={{
                  position: 'absolute',
                  top: -8,
                  right: -8,
                }}
              >
                <IconButton
                  size="small"
                  sx={{
                    width: 24,
                    height: 24,
                    background: 'rgba(255, 107, 157, 0.2)',
                    border: '1px solid rgba(255, 107, 157, 0.5)',
                    '&:hover': {
                      background: 'rgba(255, 107, 157, 0.3)',
                    },
                  }}
                >
                  <TriggerIcon sx={{ fontSize: 14, color: '#FF6B9D' }} />
                </IconButton>
              </Badge>
            </Tooltip>
          )}
        </Box>
      </Box>
    </motion.div>
  );
});

MindmapNode.displayName = 'MindmapNode';

export default MindmapNode;
