import { type Edge, type Node, Position } from '@xyflow/react';
import { AdcmJobStatus, type AdcmExecutionPlanNode, type AdcmTaskExecutionPlan } from '@models/adcm';
import { walkExecutionPlan } from './executionPlanUtils';
import { EDGE_STROKE_WIDTH, H_GAP, NODE_HEIGHT, NODE_WIDTH, V_GAP } from './layoutConstants';
import type { ExecutionGraphEdgeData, ExecutionGraphNodeData } from './types';

export type BuildFlowGraphOptions = {
  nodeWidth?: number;
  nodeHeight?: number;
  hGap?: number;
  vGap?: number;
  collapsedIds?: Set<string>;
};

export const getNodeId = (node: AdcmExecutionPlanNode): string =>
  node.kind === 'job' ? `job:${node.id}` : `group:${node.name}`;

const isCompletedStatus = (status: AdcmJobStatus): boolean =>
  status === AdcmJobStatus.Success || status === AdcmJobStatus.Aborted || status === AdcmJobStatus.Revoked;

export const getDefaultCollapsedIds = (plan: AdcmTaskExecutionPlan): Set<string> => {
  const collapsedIds = new Set<string>();

  walkExecutionPlan(plan.children, (node) => {
    if (node.kind !== 'job' && node.children.length > 0 && isCompletedStatus(node.status)) {
      collapsedIds.add(getNodeId(node));
    }
  });

  return collapsedIds;
};

export const getPlanStructureKey = (plan: AdcmTaskExecutionPlan): string => {
  const ids: string[] = [];

  walkExecutionPlan(plan.children, (node) => {
    ids.push(getNodeId(node));
  });

  return ids.join('|');
};

type PushEdgeArgs = {
  outEdges: Edge<ExecutionGraphEdgeData>[];
  source: string;
  target: string;
  sourceHandle: 'bottom' | 'right';
  targetHandle: 'top' | 'left';
};

const pushEdge = ({ outEdges, source, target, sourceHandle, targetHandle }: PushEdgeArgs) => {
  const type = sourceHandle === 'bottom' && targetHandle === 'top' ? 'straight' : 'smoothstep';

  outEdges.push({
    id: `${source}_to_${target}`,
    source,
    target,
    sourceHandle,
    targetHandle,
    type,
    className: 'graphEdge',
    data: {},
    style: { strokeWidth: EDGE_STROKE_WIDTH },
  });
};

const createFlowNode = (
  node: AdcmExecutionPlanNode,
  position: { x: number; y: number },
  isExpanded: boolean,
  size: { width: number; height: number },
): Node<ExecutionGraphNodeData> => {
  const hasChildren = node.kind !== 'job' && node.children.length > 0;

  return {
    id: getNodeId(node),
    type: 'execution',
    position,
    width: size.width,
    height: size.height,
    data: {
      entityKind: node.kind,
      entityKey: node.kind === 'job' ? String(node.id) : node.name,
      title: node.displayName || node.name,
      status: node.status,
      duration: node.duration,
      isTerminatable: node.isTerminatable,
      hasChildren,
      isExpanded: hasChildren ? isExpanded : true,
    },
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
  };
};

type LayoutContext = {
  outNodes: Node<ExecutionGraphNodeData>[];
  outEdges: Edge<ExecutionGraphEdgeData>[];
  nodeWidth: number;
  nodeHeight: number;
  hGap: number;
  vGap: number;
  collapsedIds: Set<string>;
};

const layoutSubtree = (node: AdcmExecutionPlanNode, x: number, y: number, ctx: LayoutContext): number => {
  const { outNodes, outEdges, nodeWidth, nodeHeight, hGap, vGap, collapsedIds } = ctx;
  const id = getNodeId(node);
  const hasChildren = node.kind !== 'job' && node.children.length > 0;
  const isExpanded = hasChildren ? !collapsedIds.has(id) : true;

  outNodes.push(createFlowNode(node, { x, y }, isExpanded, { width: nodeWidth, height: nodeHeight }));

  if (!hasChildren || !isExpanded) {
    return nodeHeight;
  }

  const childX = x + nodeWidth + hGap;
  let childY = y;
  let childrenHeight = 0;
  let prevChildId: string | null = null;

  node.children.forEach((child, index) => {
    const childId = getNodeId(child);
    const subtreeHeight = layoutSubtree(child, childX, childY, ctx);

    if (node.kind === 'parallel') {
      pushEdge({
        outEdges,
        source: id,
        target: childId,
        sourceHandle: 'right',
        targetHandle: 'left',
      });
    } else if (index === 0) {
      pushEdge({
        outEdges,
        source: id,
        target: childId,
        sourceHandle: 'right',
        targetHandle: 'left',
      });
    } else if (prevChildId) {
      pushEdge({
        outEdges,
        source: prevChildId,
        target: childId,
        sourceHandle: 'bottom',
        targetHandle: 'top',
      });
    }

    prevChildId = childId;
    childrenHeight += subtreeHeight + (index > 0 ? vGap : 0);
    childY += subtreeHeight + vGap;
  });

  return Math.max(nodeHeight, childrenHeight);
};

const layoutSpine = (nodes: AdcmExecutionPlanNode[], ctx: LayoutContext) => {
  let y = 0;
  let prevId: string | null = null;

  nodes.forEach((node) => {
    const id = getNodeId(node);
    const height = layoutSubtree(node, 0, y, ctx);

    if (prevId) {
      pushEdge({
        outEdges: ctx.outEdges,
        source: prevId,
        target: id,
        sourceHandle: 'bottom',
        targetHandle: 'top',
      });
    }

    prevId = id;
    y += height + ctx.vGap;
  });
};

export const buildFlowGraph = (plan: AdcmTaskExecutionPlan, options: BuildFlowGraphOptions = {}) => {
  const ctx: LayoutContext = {
    outNodes: [],
    outEdges: [],
    nodeWidth: options.nodeWidth ?? NODE_WIDTH,
    nodeHeight: options.nodeHeight ?? NODE_HEIGHT,
    hGap: options.hGap ?? H_GAP,
    vGap: options.vGap ?? V_GAP,
    collapsedIds: options.collapsedIds ?? new Set(),
  };

  layoutSpine(plan.children, ctx);

  return {
    nodes: ctx.outNodes,
    edges: ctx.outEdges,
  };
};
