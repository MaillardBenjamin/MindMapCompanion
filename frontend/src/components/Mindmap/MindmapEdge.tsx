import { memo } from 'react';
import { BaseEdge, getSmoothStepPath, type Position, EdgeLabelRenderer } from '@xyflow/react';
import { Box, Typography } from '@mui/material';

interface MindmapEdgeData {
  sourceBackendId?: number;
  targetBackendId?: number;
  showIds?: boolean;
}

interface MindmapEdgeProps {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition: Position;
  targetPosition: Position;
  style?: React.CSSProperties;
  markerEnd?: string;
  data?: MindmapEdgeData;
}

const MindmapEdge = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}: MindmapEdgeProps) => {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 20,
  });

  const showIds = data?.showIds || false;
  const sourceBackendId = data?.sourceBackendId;
  const targetBackendId = data?.targetBackendId;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={style}
      />
      {showIds && (sourceBackendId !== undefined || targetBackendId !== undefined) && (
        <EdgeLabelRenderer>
          <Box
            sx={{
              position: 'absolute',
              left: `${labelX}px`,
              top: `${labelY}px`,
              transform: 'translate(-50%, -50%)',
              backgroundColor: 'rgba(18, 24, 43, 0.95)',
              border: '1px solid rgba(0, 217, 255, 0.5)',
              borderRadius: '4px',
              padding: '2px 6px',
              pointerEvents: 'none',
              zIndex: 1000,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                fontSize: '0.65rem',
                color: '#00D9FF',
                fontFamily: 'monospace',
                whiteSpace: 'nowrap',
              }}
            >
              {sourceBackendId !== undefined && targetBackendId !== undefined
                ? `${sourceBackendId} → ${targetBackendId}`
                : sourceBackendId !== undefined
                ? `P:${sourceBackendId}`
                : `E:${targetBackendId}`}
            </Typography>
          </Box>
        </EdgeLabelRenderer>
      )}
    </>
  );
});

MindmapEdge.displayName = 'MindmapEdge';

export default MindmapEdge;
