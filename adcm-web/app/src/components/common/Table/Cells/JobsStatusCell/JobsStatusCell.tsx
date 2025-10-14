import type React from 'react';
import s from './JobsStatusCell.module.scss';
import { TableCell } from '@uikit';
import JobsStatusIcon from '@commonComponents/JobsStatusIcon/JobsStatusIcon';
import type { AdcmJobStatus } from '@models/adcm';
import cn from 'classnames';

interface JobsStatusCellProps extends React.HTMLAttributes<HTMLDivElement> {
  status: AdcmJobStatus;
  className?: string;
}

const JobsStatusCell: React.FC<JobsStatusCellProps> = ({ children, status, className }) => {
  return (
    <TableCell className={cn(s.cell, className)}>
      <JobsStatusIcon status={status} />
      {children}
    </TableCell>
  );
};

export default JobsStatusCell;
