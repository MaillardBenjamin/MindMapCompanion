import { useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  Node,
  Edge,
  NodeMouseHandler,
} from "reactflow";
import "reactflow/dist/style.css";

type MindmapViewProps = {
  nodes: Node[];
  edges: Edge[];
  onNodeClick: NodeMouseHandler;
  onNodeDragStop: (event: React.MouseEvent, node: Node) => void;
};

export default function MindmapView({
  nodes,
  edges,
  onNodeClick,
  onNodeDragStop,
}: MindmapViewProps) {
  const handleDragStop = useCallback(
    (event: React.MouseEvent, node: Node) => onNodeDragStop(event, node),
    [onNodeDragStop]
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodeClick={onNodeClick}
      onNodeDragStop={handleDragStop}
      style={{ width: "100%", height: "100%" }}
      fitView
    >
      <Background />
      <Controls />
    </ReactFlow>
  );
}
