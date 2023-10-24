import s from './JobInfoRow.module.scss';
import React from 'react';
import { AdcmJob } from '@models/adcm';
import JobsStatusIconCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusIcon/JobsStatusIcon.tsx';
import { Link } from 'react-router-dom';

interface JobInfoProps {
  job: AdcmJob;
}

const JobInfoRow: React.FC<JobInfoProps> = ({ job }: JobInfoProps) => {
  return (
    <div className={s.job}>
      <div className={s.job__id}>{job.id}</div>
      <JobsStatusIconCell size={14} status={job.status} />
      <Link className={'text-link'} to={`/jobs/${job.id}`}>
        {job.name}
      </Link>
    </div>
  );
};

export default JobInfoRow;
