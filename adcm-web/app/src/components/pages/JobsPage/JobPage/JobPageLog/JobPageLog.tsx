import React, { useState, useMemo, useEffect, RefObject, useRef, MutableRefObject } from 'react';
import { useStore } from '@hooks';
import { useRequestJobLogPage } from './useRequestJobLogPage';
import JobLog from '@commonComponents/job/JobLog/JobLog';
import JobLogsTabs from '@commonComponents/job/JobLogsTabs/JobLogsTabs';
import { AdcmJobLogItem } from '@models/adcm';
import s from './JobPageLog.module.scss';
import { Spinner } from '@uikit';
import { defaultSpinnerDelay } from '@constants';

const defaultLogs: AdcmJobLogItem[] = [];

interface JobPageLogProps {
  id: number;
  isLinkEmpty?: boolean;
  isStarted?: boolean;
  isAutoScroll?: boolean;
  setIsAutoScroll?: (isAutoScroll: boolean) => void;
  isUserScrollRef?: MutableRefObject<boolean>;
}

const JobPageLog: React.FC<JobPageLogProps> = ({
  id,
  isAutoScroll = false,
  setIsAutoScroll,
  isUserScrollRef,
  isStarted = false,
}) => {
  useRequestJobLogPage(id);
  const jobRef: RefObject<HTMLDivElement> = useRef(null);
  const childJob = useStore(({ adcm }) => adcm.jobs.task.childJobs.find((job) => job.id === id));
  const logs = useStore(({ adcm }) => adcm.jobs.jobLogs[id] ?? defaultLogs);

  const [currentLogId, setCurrentLogId] = useState<number | null>(null);
  const [isLoadedLogs, setIsLoadedLogs] = useState(false);
  const [isMinDelayEnded, setIsMinDelayEnded] = useState(false);

  useEffect(() => {
    setTimeout(() => {
      setIsMinDelayEnded(true);
    }, defaultSpinnerDelay);

    return () => {
      setIsLoadedLogs(false);
      setIsMinDelayEnded(false);
    };
  }, []);

  useEffect(() => {
    if (!isAutoScroll || logs.length === 0 || !isUserScrollRef || !jobRef?.current || !isStarted) return;

    const parentTr = jobRef.current.closest('tr');
    const prevSiblingTr = parentTr?.previousSibling as HTMLDivElement;
    const tableContainer = jobRef.current.closest('[class*="tableContainer"]') as HTMLDivElement;

    if (!parentTr || !tableContainer || !prevSiblingTr) return;
    const scrollTopTo = tableContainer.offsetTop + parentTr.offsetTop - (window.innerHeight - parentTr.scrollHeight);

    isUserScrollRef.current = false;

    window.scrollTo({
      left: 0,
      top: scrollTopTo,
      behavior: 'smooth',
    });

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logs, jobRef, jobRef?.current?.scrollHeight]);

  useEffect(() => {
    if (isMinDelayEnded && !isLoadedLogs && logs !== defaultLogs) {
      setCurrentLogId(logs[0]?.id || null);
      setIsLoadedLogs(true);
    }
  }, [logs, isLoadedLogs, isMinDelayEnded]);

  const log = useMemo(() => {
    return logs.find(({ id }) => currentLogId === id);
  }, [logs, currentLogId]);

  const onTabChange = (id: number | null) => {
    setIsAutoScroll?.(false);
    setCurrentLogId(id);
  };

  return (
    <div className={s.jobPageLog} ref={jobRef}>
      {isLoadedLogs && (
        <JobLogsTabs
          jobLogsList={logs}
          currentTabId={currentLogId}
          onChangeTab={onTabChange}
          className={s.jobLogTabs}
        />
      )}

      {!isLoadedLogs && (
        <div className={s.jobPageLog__spinner}>
          <Spinner />
        </div>
      )}

      {childJob && log && (
        <JobLog isAutoScroll={isAutoScroll} setIsAutoScroll={setIsAutoScroll} job={childJob} jobLog={log} />
      )}
    </div>
  );
};

export default JobPageLog;
