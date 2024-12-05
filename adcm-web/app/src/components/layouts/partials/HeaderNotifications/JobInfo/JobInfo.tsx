import type React from 'react';
import type { AdcmJob } from '@models/adcm';
import JobsStatusIconCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusIcon/JobsStatusIcon';
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
      {jobs.map((job) => {
        const jobName = orElseGet(job.displayName || null);
        return (
          <tr key={job.id}>
            <td className={s.job__id}>{job.id}</td>
            <td className={s.job__icon}>
              <JobsStatusIconCell dataTest={`job_status_${job.status}`} size={14} status={job.status} />
            </td>
            <td className={s.job__link}>
              <ConditionalWrapper
                Component={Tooltip}
                isWrap={jobName.length > symbolsNumberToShowTooltip}
                label={jobName}
                placement={'bottom-start'}
              >
                <Link className="text-link" to={`/jobs/${job.id}`}>
                  {jobName}
                </Link>
              </ConditionalWrapper>
            </td>
          </tr>
        );
      })}
    </table>
  );
};

export default JobInfo;
