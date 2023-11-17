import React, { useState } from 'react';
import cn from 'classnames';
import { JobLogNode } from '@commonComponents/job/JobLog/JobLogCheck/JobLogCheck.types';
import JobsStatusIconCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusIcon/JobsStatusIcon';
import { AdcmJobStatus } from '@models/adcm';
import s from './JobLogCheckNode.module.scss';
import { Collapse, IconButton } from '@uikit';

interface JobLogCheckNodeProps {
  logNode: JobLogNode;
  isExpanded: boolean;
  onExpand: (isOpen: boolean) => void;
}
const JobLogCheckNode: React.FC<JobLogCheckNodeProps> = ({ logNode: { data, key }, isExpanded, onExpand }) => {
  let status: AdcmJobStatus = data.result ? AdcmJobStatus.Success : AdcmJobStatus.Failed;

  if (key === 'root' && data.jobStatus === AdcmJobStatus.Running) {
    status = AdcmJobStatus.Running;
  }

  const statusLabel = data.result ? 'success' : 'failed';

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
    <div className={cn(s.jobLogCheckNode, { 'is-open': isOpen, 'is-failed': !data.result })}>
      <div className={s.jobLogCheckNode__header}>
        <span className={s.jobLogCheckNode__iconWrapper}>
          <JobsStatusIconCell status={status} size={14} />
        </span>

        <span className={s.jobLogCheckNode__status}>{statusLabel}</span>

        <span className={s.jobLogCheckNode__title} onClick={handleExpandClick}>
          {data.title}
        </span>

        <span className={s.jobLogCheckNode__iconWrapper}>
          <IconButton
            icon="chevron"
            size={12}
            className={cn(s.jobLogCheckNode__arrow, {
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
            <div className={s.jobLogCheckNode__messagePanel}>
              <div className={cn(s.jobLogCheckNode__message, 'scroll')}>{data.message || '...'}</div>
            </div>
          </Collapse>
        </div>
      )}
    </div>
  );
};

export default JobLogCheckNode;
