import { AdcmJobStatus } from '@models/adcm';
import type { AdcmTaskExecutionPlan } from '@models/adcm';
import { buildFlowGraph, getDefaultCollapsedIds } from './buildFlowGraph';
import { H_GAP, NODE_WIDTH } from './layoutConstants';

const flatPlan: AdcmTaskExecutionPlan = {
  version: 1,
  children: [
    {
      kind: 'job',
      id: 1,
      name: 'pre',
      displayName: 'Pre',
      status: AdcmJobStatus.Success,
      startTime: null,
      endTime: null,
      duration: 1,
      isTerminatable: true,
    },
    {
      kind: 'job',
      id: 2,
      name: 'post',
      displayName: 'Post',
      status: AdcmJobStatus.Created,
      startTime: null,
      endTime: null,
      duration: null,
      isTerminatable: true,
    },
  ],
};

const parallelPlan: AdcmTaskExecutionPlan = {
  version: 1,
  children: [
    {
      kind: 'parallel',
      name: 'shards',
      displayName: 'Shards',
      status: AdcmJobStatus.Running,
      startTime: null,
      endTime: null,
      duration: null,
      isTerminatable: true,
      children: [
        {
          kind: 'job',
          id: 10,
          name: 'a',
          displayName: 'A',
          status: AdcmJobStatus.Success,
          startTime: null,
          endTime: null,
          duration: 2,
          isTerminatable: true,
        },
        {
          kind: 'job',
          id: 11,
          name: 'b',
          displayName: 'B',
          status: AdcmJobStatus.Failed,
          startTime: null,
          endTime: null,
          duration: 3,
          isTerminatable: true,
        },
      ],
    },
  ],
};

const completedGroupPlan: AdcmTaskExecutionPlan = {
  version: 1,
  children: [
    {
      kind: 'parallel',
      name: 'done',
      displayName: 'Done',
      status: AdcmJobStatus.Success,
      startTime: null,
      endTime: null,
      duration: 5,
      isTerminatable: false,
      children: [
        {
          kind: 'job',
          id: 20,
          name: 'child',
          displayName: 'Child',
          status: AdcmJobStatus.Success,
          startTime: null,
          endTime: null,
          duration: 5,
          isTerminatable: false,
        },
      ],
    },
  ],
};

describe('buildFlowGraph', () => {
  it('chains root children vertically on the spine', () => {
    const { nodes, edges } = buildFlowGraph(flatPlan);
    expect(nodes.map((n) => n.id)).toEqual(['job:1', 'job:2']);
    expect(edges.map((e) => e.id)).toContain('job:1_to_job:2');
    expect(nodes[0].position.x).toBe(0);
    expect(nodes[1].position.x).toBe(0);
    expect(nodes[0].position.y).toBeLessThan(nodes[1].position.y);
  });

  it('places parallel children to the right of the group node', () => {
    const { nodes, edges } = buildFlowGraph(parallelPlan);
    const group = nodes.find((n) => n.id === 'group:shards');
    const childA = nodes.find((n) => n.id === 'job:10');
    const childB = nodes.find((n) => n.id === 'job:11');

    expect(group).toBeDefined();
    expect(childA).toBeDefined();
    expect(childB).toBeDefined();
    expect(childA!.position.x).toBeGreaterThan(group!.position.x);
    expect(childB!.position.x).toBe(childA!.position.x);
    expect(childB!.position.y).toBeGreaterThan(childA!.position.y);
    expect(childA!.position.x - group!.position.x).toBe(NODE_WIDTH + H_GAP);
    expect(edges.map((e) => `${e.source}_to_${e.target}`)).toEqual(
      expect.arrayContaining(['group:shards_to_job:10', 'group:shards_to_job:11']),
    );
  });

  it('uses neutral edge class without status colors', () => {
    const { edges } = buildFlowGraph(parallelPlan);
    const edge = edges.find((e) => e.source === 'group:shards' && e.target === 'job:11');
    expect(edge?.className).toBe('graphEdge');
  });

  it('hides children of collapsed groups', () => {
    const collapsedIds = getDefaultCollapsedIds(completedGroupPlan);
    expect(collapsedIds.has('group:done')).toBe(true);

    const { nodes, edges } = buildFlowGraph(completedGroupPlan, { collapsedIds });
    expect(nodes.map((n) => n.id)).toEqual(['group:done']);
    expect(edges).toHaveLength(0);
  });
});
