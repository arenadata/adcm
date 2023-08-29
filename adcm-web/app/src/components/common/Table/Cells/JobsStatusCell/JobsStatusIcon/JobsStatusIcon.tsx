import React from 'react';
import cn from 'classnames';
import s from './JobsStatusIcon.module.scss';
import { Icon } from '@uikit';
import { AdcmJobStatus } from '@models/adcm';
import { jobStatusesIconsMap } from './JobsStatusIcon.constants';

interface JobsTableStatusIconProps extends React.HTMLAttributes<HTMLDivElement> {
  status: AdcmJobStatus;
}

const JobsStatusIconCell: React.FC<JobsTableStatusIconProps> = ({ status }) => {
  const classes = cn(s.status, s[`status_${status.toLowerCase()}`]);
  return (
    <>
      <Icon name={jobStatusesIconsMap[status]} size={10} className={classes} />
    </>
  );
};

export default JobsStatusIconCell;
