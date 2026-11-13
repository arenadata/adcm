import type React from 'react';
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import cn from 'classnames';
import { Tooltip } from '@uikit';
import JobsStatusIcon from '@commonComponents/JobsStatusIcon/JobsStatusIcon';
import { JobActionIconButton } from '@commonComponents/job/JobActionIconButton/JobActionIconButton';
import { getJobTerminateActions } from '@commonComponents/job/jobTerminateActions';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import { useJobExecutionGraphContext } from '../JobExecutionGraph.context';
import { CARD_WIDTH, CONNECTOR_WIDTH, DISCLOSURE_WIDTH, STATUS_ICON_SIZE } from '../layoutConstants';
import type { ExecutionGraphNodeData } from '../types';
import s from './ExecutionGraphNode.module.scss';

export type ExecutionGraphFlowNode = Node<ExecutionGraphNodeData, 'execution'>;

const CARD_LEFT = DISCLOSURE_WIDTH + CONNECTOR_WIDTH;
const CARD_CENTER_X = CARD_LEFT + CARD_WIDTH / 2;
const graphActionClassName = cn('nodrag', 'nopan');

export const ExecutionGraphNode = ({ id, data }: NodeProps<ExecutionGraphFlowNode>) => {
  const { onNodeAction, onToggleExpand } = useJobExecutionGraphContext();
  const duration = data.duration !== null ? secondsToDuration(data.duration) : '-';
  const { isSkipEnabled, isStopEnabled } = getJobTerminateActions(data);

  const handleSkipClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    event.preventDefault();
    onNodeAction?.({ nodeId: id, data, action: 'skip' });
  };

  const handleStopClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    event.preventDefault();
    onNodeAction?.({ nodeId: id, data, action: 'stop' });
  };

  const handleToggleExpand = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    event.preventDefault();
    onToggleExpand?.(id);
  };

  return (
    <div
      className={s.root}
      data-test="execution-graph-node"
      data-entity-kind={data.entityKind}
      data-entity-key={data.entityKey}
    >
      <div className={s.disclosure}>
        {data.hasChildren && (
          <button
            type="button"
            className={cn(s.expandToggle, 'nodrag', 'nopan')}
            onClick={handleToggleExpand}
            title={data.isExpanded ? 'Collapse' : 'Expand'}
            data-test="execution-graph-node-expand"
          >
            {data.isExpanded ? '-' : '+'}
          </button>
        )}
      </div>

      <div className={cn(s.connector, { [s.connector_linked]: data.hasChildren })} aria-hidden />

      <div className={cn(s.node, s[`node_${data.status}`])}>
        <JobsStatusIcon status={data.status} size={STATUS_ICON_SIZE} />
        <Tooltip label={data.title} placement="top">
          <div className={cn(s.titleWrap, 'nodrag', 'nopan')}>
            <span className={s.title}>{data.title}</span>
          </div>
        </Tooltip>
        <span className={s.duration}>{duration}</span>
        <div className={s.actions}>
          <JobActionIconButton
            icon="g1-graph-skip"
            label="Skip"
            className={graphActionClassName}
            disabled={!isSkipEnabled}
            onClick={handleSkipClick}
            data-test="execution-graph-node-skip"
          />
          <JobActionIconButton
            icon="g1-graph-stop"
            label="Stop"
            className={graphActionClassName}
            disabled={!isStopEnabled}
            onClick={handleStopClick}
            data-test="execution-graph-node-action"
          />
        </div>
      </div>

      <Handle type="target" id="top" position={Position.Top} className={s.handle} style={{ left: CARD_CENTER_X }} />
      <Handle type="target" id="left" position={Position.Left} className={s.handle} style={{ left: CARD_LEFT }} />
      <Handle
        type="source"
        id="bottom"
        position={Position.Bottom}
        className={s.handle}
        style={{ left: CARD_CENTER_X }}
      />
      <Handle type="source" id="right" position={Position.Right} className={s.handle} />
    </div>
  );
};
