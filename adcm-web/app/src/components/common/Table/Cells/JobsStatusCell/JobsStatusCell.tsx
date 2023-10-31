import React from 'react';
import s from './JobsStatusCell.module.scss';
import { TableCell } from '@uikit';
import JobsStatusIconCell from './JobsStatusIcon/JobsStatusIcon';
import { AdcmJobStatus } from '@models/adcm';
import cn from 'classnames';

interface JobsStatusCellProps extends React.HTMLAttributes<HTMLDivElement> {
  status: AdcmJobStatus;
  className?: string;
}

const JobsStatusCell: React.FC<JobsStatusCellProps> = ({ children, status, className }) => {
  return (
    <TableCell className={cn(s.cell, className)}>
      <JobsStatusIconCell status={status} />
      {children}
    </TableCell>
  );
};

export default JobsStatusCell;
