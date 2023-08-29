import React from 'react';
import s from './JobsStatusCell.module.scss';
import { TableCell } from '@uikit';
import JobsStatusIconCell from './JobsStatusIcon/JobsStatusIcon';
import { AdcmJobStatus } from '@models/adcm';

interface JobsStatusCellProps extends React.HTMLAttributes<HTMLDivElement> {
  status: AdcmJobStatus;
}

const JobsStatusCell: React.FC<JobsStatusCellProps> = ({ children, status }) => {
  return (
    <TableCell className={s.cell}>
      <JobsStatusIconCell status={status} />
      {children}
    </TableCell>
  );
};

export default JobsStatusCell;
