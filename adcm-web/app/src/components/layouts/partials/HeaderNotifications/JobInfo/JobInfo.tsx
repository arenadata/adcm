import React from 'react';
import { AdcmJob } from '@models/adcm';
import JobsStatusIconCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusIcon/JobsStatusIcon.tsx';
import { Link } from 'react-router-dom';
import { ConditionalWrapper, Tooltip } from '@uikit';
import s from './JobInfo.module.scss';

interface JobInfoProps {
  jobs: AdcmJob[];
}

const symbolsNumberToShowTooltip = 16;

const JobInfo: React.FC<JobInfoProps> = ({ jobs }) => {
  if (jobs.length === 0) return null;

  return (
    <table className={s.jobs}>
      {jobs.map((job) => (
        <tr key={job.id}>
          <td className={s.job__id}>{job.id}</td>
          <td className={s.job__icon}>
            <JobsStatusIconCell size={14} status={job.status} />
          </td>
          <td className={s.job__link}>
            {job?.name && (
              <ConditionalWrapper
                Component={Tooltip}
                isWrap={job.name.length > symbolsNumberToShowTooltip}
                label={job.name}
                placement={'bottom-start'}
              >
                <Link className="text-link" to={`/jobs/${job.id}`}>
                  {job.displayName}
                </Link>
              </ConditionalWrapper>
            )}
          </td>
        </tr>
      ))}
    </table>
  );
};

export default JobInfo;
