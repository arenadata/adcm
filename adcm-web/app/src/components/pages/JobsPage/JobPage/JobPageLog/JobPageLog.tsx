import React, { useState, useMemo, useEffect } from 'react';
import { useStore } from '@hooks';
import { useRequestJobLogPage } from './useRequestJobLogPage';
import JobLog from '@commonComponents/job/JobLog/JobLog';
import JobLogsTabs from '@commonComponents/job/JobLogsTabs/JobLogsTabs';
import { AdcmJobLogItem } from '@models/adcm';
import s from './JobPageLog.module.scss';

const defaultLogs: AdcmJobLogItem[] = [];

interface JobPageLogProps {
  id: number;
  isLinkEmpty?: boolean;
}

const JobPageLog: React.FC<JobPageLogProps> = ({ id }) => {
  useRequestJobLogPage(id);

  const childJob = useStore(({ adcm }) => adcm.jobs.task.childJobs.find((job) => job.id === id));
  const logs = useStore(({ adcm }) => adcm.jobs.jobLogs[id] ?? defaultLogs);

  const [currentLogId, setCurrentLogId] = useState<number | null>(null);
  const [isLoadedLogs, setIsLoadedLogs] = useState(false);

  useEffect(
    () => () => {
      setIsLoadedLogs(false);
    },
    [],
  );

  useEffect(() => {
    if (!isLoadedLogs && logs !== defaultLogs) {
      setCurrentLogId(logs[0]?.id || null);
      setIsLoadedLogs(true);
    }
  }, [logs, isLoadedLogs]);

  const log = useMemo(() => {
    return logs.find(({ id }) => currentLogId === id);
  }, [logs, currentLogId]);

  return (
    <div className={s.jobPageLog}>
      <JobLogsTabs
        jobLogsList={logs}
        currentTabId={currentLogId}
        onChangeTab={setCurrentLogId}
        className={s.jobLogTabs}
      />

      {childJob && log && <JobLog job={childJob} jobLog={log} />}
    </div>
  );
};

export default JobPageLog;
