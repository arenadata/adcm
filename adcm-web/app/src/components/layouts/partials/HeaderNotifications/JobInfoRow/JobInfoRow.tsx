import s from './JobInfoRow.module.scss';
import React from 'react';
import { AdcmJob } from '@models/adcm';
import JobsStatusIconCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusIcon/JobsStatusIcon.tsx';
import { Link } from 'react-router-dom';
import { ConditionalWrapper, Tooltip } from '@uikit';
import cn from 'classnames';

interface JobInfoProps {
  job: AdcmJob;
}

const symbolsNumberToShowTooltip = 16;

const JobInfoRow: React.FC<JobInfoProps> = ({ job }: JobInfoProps) => {
  return (
    <div className={s.job}>
      <div className={s.job__id}>{job.id}</div>
      <JobsStatusIconCell size={14} status={job.status} />
      <ConditionalWrapper
        Component={Tooltip}
        isWrap={job.name.length > symbolsNumberToShowTooltip}
        label={job.name}
        placement={'bottom-start'}
      >
        <Link className={cn(s.job__link, 'text-link')} to={`/jobs/${job.id}`}>
          {job.name}
        </Link>
      </ConditionalWrapper>
    </div>
  );
};

export default JobInfoRow;
