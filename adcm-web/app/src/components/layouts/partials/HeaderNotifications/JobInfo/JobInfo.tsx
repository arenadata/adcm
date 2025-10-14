import type React from 'react';
import type { AdcmJob } from '@models/adcm';
import s from './JobInfo.module.scss';
import JobInfoTableRow from './JobInfoTableRow';
import { Switch } from '@uikit';
import { useLocalStorage } from '@hooks';

interface JobInfoProps {
  jobs: AdcmJob[];
}

const JobInfo: React.FC<JobInfoProps> = ({ jobs }) => {
  if (jobs.length === 0) return <div className={s.noData}>No data</div>;

  const [isExpanded, saveIsExpandedToStorage] = useLocalStorage<string>({
    key: 'are_job_details_expanded',
    initData: 'true',
  });

  const isRowExpanded = isExpanded === 'true';

  const handleSwitchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    saveIsExpandedToStorage(String(event.target.checked));
  };

  return (
    <>
      <table className={s.jobs} data-test="jobs-notification-table">
        {jobs.map((job) => (
          <JobInfoTableRow key={job.id} job={job} areAllExpanded={isRowExpanded} />
        ))}
      </table>
      <div className={s.jobs__toggleAllSwitch}>
        <Switch label="Details" isToggled={isRowExpanded} onChange={handleSwitchChange} />
      </div>
    </>
  );
};

export default JobInfo;
