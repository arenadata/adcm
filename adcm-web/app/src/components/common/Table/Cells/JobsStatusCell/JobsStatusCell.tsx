import type React from 'react';
import s from './JobsStatusCell.module.scss';
import { TableCell, Tooltip, Icon } from '@uikit';
import JobsStatusIcon from '@commonComponents/JobsStatusIcon/JobsStatusIcon';
import type { AdcmJobStatus } from '@models/adcm';
import cn from 'classnames';

interface JobsStatusCellProps extends React.HTMLAttributes<HTMLDivElement> {
  status: AdcmJobStatus;
  className?: string;
  description?: string | null;
}

const JobsStatusCell: React.FC<JobsStatusCellProps> = ({ children, status, className, description }) => {
  return (
    <TableCell className={cn(s.cell, className)}>
      <JobsStatusIcon status={status} />
      {children}
      {description && (
        <Tooltip label={description} placement="bottom-start">
          <Icon name="hint" />
        </Tooltip>
      )}
    </TableCell>
  );
};

export default JobsStatusCell;
