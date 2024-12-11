import type React from 'react';
import { useState } from 'react';
import cn from 'classnames';
import type { SubJobLogNode } from '@commonComponents/job/SubJobLog/SubJobLogCheck/SubJobLogCheck.types';
import JobsStatusIconCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusIcon/JobsStatusIcon';
import { AdcmJobStatus } from '@models/adcm';
import s from './SubJobLogCheckNode.module.scss';
import { Collapse, IconButton } from '@uikit';

interface SubJobLogCheckNodeProps {
  logNode: SubJobLogNode;
  isExpanded: boolean;
  onExpand: (isOpen: boolean) => void;
}
const SubJobLogCheckNode: React.FC<SubJobLogCheckNodeProps> = ({ logNode: { data, key }, isExpanded, onExpand }) => {
  let status: AdcmJobStatus = data.result ? AdcmJobStatus.Success : AdcmJobStatus.Failed;
  let statusLabel = data.result ? 'success' : 'failed';

  if (key === 'root' && data.subJobStatus === AdcmJobStatus.Running) {
    status = AdcmJobStatus.Running;
    statusLabel = 'processing';
  }

  const hasChildren = data.type === 'group';

  const [isLocalExpand, setLocalExpand] = useState(false);

  const isOpen = hasChildren ? isExpanded : isLocalExpand;

  const handleExpandClick = () => {
    if (hasChildren) {
      onExpand(!isExpanded);
    } else {
      setLocalExpand((prev) => !prev);
    }
  };

  return (
    <div className={cn(s.subJobLogCheckNode, { 'is-open': isOpen, 'is-failed': !data.result })}>
      <div className={s.subJobLogCheckNode__header}>
        <span className={s.subJobLogCheckNode__iconWrapper}>
          <JobsStatusIconCell status={status} size={14} />
        </span>

        <span className={s.subJobLogCheckNode__status}>{statusLabel}</span>

        <span className={s.subJobLogCheckNode__title} onClick={handleExpandClick}>
          {data.title}
        </span>

        <span className={s.subJobLogCheckNode__iconWrapper}>
          <IconButton
            icon="chevron"
            size={12}
            className={cn(s.subJobLogCheckNode__arrow, {
              [s.jobLogCheckNode__arrow_up]: isOpen,
            })}
            onClick={handleExpandClick}
            data-test="expand-btn"
          />
        </span>
      </div>
      {data.type === 'check' && (
        <div>
          <Collapse isExpanded={isLocalExpand}>
            <div className={s.subJobLogCheckNode__messagePanel}>
              <div className={cn(s.subJobLogCheckNode__message, 'scroll')}>{data.message || '...'}</div>
            </div>
          </Collapse>
        </div>
      )}
    </div>
  );
};

export default SubJobLogCheckNode;
