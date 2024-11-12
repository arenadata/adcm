import React from 'react';
import type { AdcmJob, AdcmJobLogItem } from '@models/adcm';
import { AdcmJobLogType } from '@models/adcm';
import DownloadJobLog from './DownloadJobLog/DownloadJobLog';
import JobLogCheck from './JobLogCheck/JobLogCheck';
import JobLogText from './JobLogText/JobLogText';

interface JobLogProps {
  job: AdcmJob;
  jobLog: AdcmJobLogItem;
  isAutoScroll: boolean;
  setIsAutoScroll?: (isAutoScroll: boolean) => void;
}

const JobLog: React.FC<JobLogProps> = ({ job, jobLog, isAutoScroll, setIsAutoScroll }) => {
  return (
    <>
      {renderLog({ job, jobLog, isAutoScroll, setIsAutoScroll })}
      {jobLog.content && <DownloadJobLog jobId={job.id} jobLogId={jobLog.id} />}
    </>
  );
};
export default JobLog;

const renderLog = ({ job, jobLog, isAutoScroll, setIsAutoScroll }: JobLogProps) => {
  if (jobLog.type === AdcmJobLogType.Check) {
    return <JobLogCheck log={jobLog} jobStatus={job.status} />;
  }

  return <JobLogText isAutoScroll={isAutoScroll} setIsAutoScroll={setIsAutoScroll} log={jobLog} />;
};
