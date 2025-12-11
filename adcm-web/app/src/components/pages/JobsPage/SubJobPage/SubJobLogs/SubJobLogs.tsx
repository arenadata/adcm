import { useState, useMemo, useEffect } from 'react';
import { useStore } from '@hooks';
import { useRequestSubJobLogs } from './useRequestSubJobLogs';
import SubJobLog from '@commonComponents/job/SubJobLog/SubJobLog';
import SubJobLogsTabs from '@commonComponents/job/SubJobLogsTabs/SubJobLogsTabs';
import s from './SubJobLogs.module.scss';
import { Spinner } from '@uikit';
import { FullscreenContainer } from '@uikit/CodeHighlighter/SubComponents/FullscreenContainer';

const SubJobLogs = () => {
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

  const content = (
    <>
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
      {subJob && log && <SubJobLog subJob={subJob} subJobLog={log} />}
    </>
  );

  return <FullscreenContainer className={s.subJobLog}>{content}</FullscreenContainer>;
};

export default SubJobLogs;
