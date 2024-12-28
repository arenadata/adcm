import type React from 'react';
import cn from 'classnames';
import s from './JobsStatusIcon.module.scss';
import { Icon } from '@uikit';
import { AdcmJobStatus } from '@models/adcm';
import { jobStatusesIconsMap } from './JobsStatusIcon.constants';

interface JobsTableStatusIconProps extends React.HTMLAttributes<HTMLDivElement> {
  status: AdcmJobStatus;
  size?: number;
  dataTest?: string;
}

// todo: rename and replace this component. This is not Cell
const JobsStatusIconCell: React.FC<JobsTableStatusIconProps> = ({ status, dataTest, size = 10 }) => {
  const classes = cn(s.status, s[`status_${status.toLowerCase()}`], {
    spin: status === AdcmJobStatus.Running,
  });

  return (
    <>
      <Icon data-test={dataTest} name={jobStatusesIconsMap[status]} size={size} className={classes} />
    </>
  );
};

export default JobsStatusIconCell;
