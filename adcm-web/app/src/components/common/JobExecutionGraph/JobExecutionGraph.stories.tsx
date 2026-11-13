import type { Meta, StoryObj } from '@storybook/react';
import { useMemo, useState } from 'react';
import JobExecutionGraph from './JobExecutionGraph';
import { advanceBaculaStatuses, baculaLikePlan, flatPlan } from './JobExecutionGraph.stories.fixtures';
import type { ExecutionGraphNodeData } from './types';

const meta = {
  title: 'common/JobExecutionGraph',
  component: JobExecutionGraph,
  parameters: { layout: 'fullscreen' },
} satisfies Meta<typeof JobExecutionGraph>;

export default meta;

type Story = StoryObj<typeof JobExecutionGraph>;

type PlanPreset = 'bacula' | 'flat';

const plans: Record<PlanPreset, typeof baculaLikePlan> = {
  bacula: baculaLikePlan,
  flat: flatPlan,
};

export const Playground: Story = {
  render: () => {
    const [preset, setPreset] = useState<PlanPreset>('bacula');
    const [plan, setPlan] = useState(baculaLikePlan);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>('job:100');
    const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
    const [lastAction, setLastAction] = useState<ExecutionGraphNodeData | null>(null);

    const toolbarStyle = useMemo(
      () =>
        ({
          display: 'flex',
          flexWrap: 'wrap',
          gap: 12,
          alignItems: 'center',
          padding: '10px 14px',
          fontSize: 13,
          color: 'var(--text-primary, inherit)',
          background: 'var(--body-background, transparent)',
          borderBottom: '1px solid var(--color-stroke-light, #3d4450)',
        }) as const,
      [],
    );

    const applyPreset = (next: PlanPreset) => {
      setPreset(next);
      setPlan(plans[next]);
      setSelectedNodeId(next === 'bacula' ? 'job:100' : null);
      setLastAction(null);
    };

    return (
      <div style={{ height: '100vh', width: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={toolbarStyle}>
          <label>
            Plan{' '}
            <select value={preset} onChange={(event) => applyPreset(event.target.value as PlanPreset)}>
              <option value="bacula">Bacula (nested)</option>
              <option value="flat">Flat jobs</option>
            </select>
          </label>
          <button
            type="button"
            onClick={() => setPlan((prev) => advanceBaculaStatuses(prev))}
            disabled={preset !== 'bacula'}
          >
            Advance statuses
          </button>
          <button type="button" onClick={() => applyPreset(preset)}>
            Reset plan
          </button>
          <span>
            selected: <strong>{selectedNodeId ?? '-'}</strong>
          </span>
          <span>
            hovered: <strong>{hoveredNodeId ?? '-'}</strong>
          </span>
          <span>
            last action:{' '}
            <strong>
              {lastAction ? `${lastAction.title} (${lastAction.entityKind}:${lastAction.entityKey})` : '-'}
            </strong>
          </span>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          <JobExecutionGraph
            plan={plan}
            selectedNodeId={selectedNodeId}
            onNodeClick={({ nodeId }) => setSelectedNodeId(nodeId)}
            onNodeMouseEnter={({ nodeId }) => setHoveredNodeId(nodeId)}
            onNodeMouseLeave={() => setHoveredNodeId(null)}
            onNodeAction={({ data, action }) => {
              setLastAction({ ...data, title: `${action}: ${data.title}` });
            }}
          />
        </div>
      </div>
    );
  },
};
