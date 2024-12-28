import { useState, useMemo, useEffect } from 'react';
import { useStore } from '@hooks';
import { useRequestSubJobLogs } from './useRequestSubJobLogs';
import SubJobLog from '@commonComponents/job/SubJobLog/SubJobLog';
import SubJobLogsTabs from '@commonComponents/job/SubJobLogsTabs/SubJobLogsTabs';
import s from './SubJobLogs.module.scss';
import { Spinner } from '@uikit';

export interface SubJobLogsProps {
  isAutoScroll: boolean;
  setIsAutoScroll: (value: boolean) => void;
}

const SubJobLogs = ({ isAutoScroll, setIsAutoScroll }: SubJobLogsProps) => {
  const subJob = useStore(({ adcm }) => adcm.subJob.subJob);
  const subJobLogs = useStore(({ adcm }) => adcm.subJob.subJobLog);

  useRequestSubJobLogs();

  const [currentLogId, setCurrentLogId] = useState<number | null>(null);
  const [isSubJobLogsShown, setIsSubJobLogsShown] = useState(false);

  useEffect(() => {
    if (subJobLogs.length > 0 && !isSubJobLogsShown) {
      setCurrentLogId(subJobLogs[0].id || null);
      setIsSubJobLogsShown(true);
    }
  }, [subJobLogs, isSubJobLogsShown]);

  const log = useMemo(() => {
    return subJobLogs.find(({ id }) => currentLogId === id);
  }, [subJobLogs, currentLogId]);

  const onTabChange = (id: number | null) => {
    setCurrentLogId(id);
  };

  return (
    <div className={s.subJobLog}>
      {isSubJobLogsShown && (
        <SubJobLogsTabs
          subJobId={subJob?.id}
          subJobLogsList={subJobLogs}
          currentTabId={currentLogId}
          onChangeTab={onTabChange}
        />
      )}

      {!isSubJobLogsShown && (
        <div className={s.subJobLog__spinner}>
          <Spinner />
        </div>
      )}

      {subJob && log && (
        <SubJobLog isAutoScroll={isAutoScroll} setIsAutoScroll={setIsAutoScroll} subJob={subJob} subJobLog={log} />
      )}
    </div>
  );
};

export default SubJobLogs;
