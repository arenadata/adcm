import React from 'react';
import { AdcmJob, AdcmJobLogItem, AdcmJobLogType } from '@models/adcm';
import DownloadJobLog from './DownloadJobLog/DownloadJobLog';
import JobLogCheck from './JobLogCheck/JobLogCheck';
import JobLogText from './JobLogText/JobLogText';

interface JobLogProps {
  job: AdcmJob;
  jobLog: AdcmJobLogItem;
}

const JobLog: React.FC<JobLogProps> = ({ job, jobLog }) => {
  return (
    <>
      {renderLog({ job, jobLog })}
      {jobLog.content && <DownloadJobLog jobId={job.id} jobLogId={jobLog.id} />}
    </>
  );
};
export default JobLog;

const renderLog = ({ job, jobLog }: JobLogProps) => {
  if (jobLog.type === AdcmJobLogType.Check) {
    return <JobLogCheck log={jobLog} jobStatus={job.status} />;
  }

  return <JobLogText log={jobLog} />;
};
