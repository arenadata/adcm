import React from 'react';
import { AdcmJob } from '@models/adcm';
import JobsStatusIconCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusIcon/JobsStatusIcon.tsx';
import { Link } from 'react-router-dom';
import { ConditionalWrapper, Tooltip } from '@uikit';
import s from './JobInfo.module.scss';
import { orElseGet } from '@utils/checkUtils';

interface JobInfoProps {
  jobs: AdcmJob[];
}

const symbolsNumberToShowTooltip = 16;

const JobInfo: React.FC<JobInfoProps> = ({ jobs }) => {
  if (jobs.length === 0) return <div className={s.noData}>No data</div>;

  return (
    <table className={s.jobs} data-test="jobs-notification-table">
      {jobs.map((job) => (
        <tr key={job.id}>
          <td className={s.job__id}>{job.id}</td>
          <td className={s.job__icon}>
            <JobsStatusIconCell dataTest={'job_status_' + job.status} size={14} status={job.status} />
          </td>
          <td className={s.job__link}>
            {job?.displayName && (
              <ConditionalWrapper
                Component={Tooltip}
                isWrap={job.displayName.length > symbolsNumberToShowTooltip}
                label={job.displayName}
                placement={'bottom-start'}
              >
                <Link className="text-link" to={`/jobs/${job.id}`}>
                  {orElseGet(job.displayName || '-')}
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
