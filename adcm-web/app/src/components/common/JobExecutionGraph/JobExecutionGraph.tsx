import { useCallback, useEffect, useMemo, useState } from 'react';
import { type NodeMouseHandler, ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import cn from 'classnames';
import type { AdcmTaskExecutionPlan } from '@models/adcm';
import { buildFlowGraph, getDefaultCollapsedIds, getPlanStructureKey } from './buildFlowGraph';
import { JobExecutionGraphContext, type JobExecutionGraphNodeActionPayload } from './JobExecutionGraph.context';
import GraphZoomControls from './GraphZoomControls/GraphZoomControls';
import { GRAPH_CONTENT_PADDING_BOTTOM, INITIAL_VIEWPORT, MAX_ZOOM, MIN_ZOOM, NODE_HEIGHT } from './layoutConstants';
import { ExecutionGraphNode } from './nodes/ExecutionGraphNode';
import type { ExecutionGraphNodeData } from './types';
import s from './JobExecutionGraph.module.scss';

const nodeTypes = { execution: ExecutionGraphNode };

export type JobExecutionGraphProps = {
  plan: AdcmTaskExecutionPlan;
  className?: string;
  selectedNodeId?: string | null;
  onNodeClick?: (payload: { nodeId: string; data: ExecutionGraphNodeData }) => void;
  onNodeMouseEnter?: (payload: { nodeId: string; data: ExecutionGraphNodeData }) => void;
  onNodeMouseLeave?: () => void;
  onNodeAction?: (payload: JobExecutionGraphNodeActionPayload) => void;
};

const JobExecutionGraph = ({
  plan,
  className,
  selectedNodeId,
  onNodeClick,
  onNodeMouseEnter,
  onNodeMouseLeave,
  onNodeAction,
}: JobExecutionGraphProps) => {
  const planStructureKey = useMemo(() => getPlanStructureKey(plan), [plan]);
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(() => getDefaultCollapsedIds(plan));

  useEffect(() => {
    setCollapsedIds(getDefaultCollapsedIds(plan));
  }, [planStructureKey]);

  const { nodes, edges } = useMemo(() => buildFlowGraph(plan, { collapsedIds }), [plan, collapsedIds]);

  const contentHeight = useMemo(() => {
    let maxBottom = 0;
    for (const node of nodes) {
      maxBottom = Math.max(maxBottom, node.position.y + (node.height ?? NODE_HEIGHT));
    }
    return maxBottom + INITIAL_VIEWPORT.y + GRAPH_CONTENT_PADDING_BOTTOM;
  }, [nodes]);

  const nodesWithSelection = useMemo(
    () => nodes.map((node) => ({ ...node, selected: node.id === selectedNodeId })),
    [nodes, selectedNodeId],
  );

  const handleToggleExpand = useCallback((nodeId: string) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  const contextValue = useMemo(
    () => ({ onNodeAction, onToggleExpand: handleToggleExpand }),
    [onNodeAction, handleToggleExpand],
  );

  const handleClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      onNodeClick?.({ nodeId: node.id, data: node.data as ExecutionGraphNodeData });
    },
    [onNodeClick],
  );

  const handleMouseEnter: NodeMouseHandler = useCallback(
    (_event, node) => {
      onNodeMouseEnter?.({ nodeId: node.id, data: node.data as ExecutionGraphNodeData });
    },
    [onNodeMouseEnter],
  );

  const handleMouseLeave: NodeMouseHandler = useCallback(() => {
    onNodeMouseLeave?.();
  }, [onNodeMouseLeave]);

  if (plan.children.length === 0) {
    return (
      <div className={cn(s.empty, className)} data-test="job-execution-graph-empty">
        No execution plan nodes
      </div>
    );
  }

  return (
    <JobExecutionGraphContext.Provider value={contextValue}>
      <div className={cn(s.wrapper, className)} style={{ height: contentHeight }} data-test="job-execution-graph">
        <ReactFlow
          nodes={nodesWithSelection}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={handleClick}
          onNodeMouseEnter={handleMouseEnter}
          onNodeMouseLeave={handleMouseLeave}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          defaultViewport={INITIAL_VIEWPORT}
          minZoom={MIN_ZOOM}
          maxZoom={MAX_ZOOM}
          zoomOnScroll={false}
          preventScrolling={false}
          proOptions={{ hideAttribution: true }}
        >
          <GraphZoomControls />
        </ReactFlow>
      </div>
    </JobExecutionGraphContext.Provider>
  );
};

export default JobExecutionGraph;
