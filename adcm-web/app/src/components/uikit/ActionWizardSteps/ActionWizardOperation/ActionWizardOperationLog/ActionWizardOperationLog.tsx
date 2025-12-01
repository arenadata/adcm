import type React from 'react';
import { useEffect, useMemo, useState } from 'react';
import s from './ActionWizardOperationLog.module.scss';
import SubJobLogsTabs from '@commonComponents/job/SubJobLogsTabs/SubJobLogsTabs';
import { Spinner } from '@uikit';
import SubJobLog from '@commonComponents/job/SubJobLog/SubJobLog';
import type { AdcmSubJob, AdcmSubJobLogItem } from '@models/adcm';

export interface ActionWizardOperationLogProps {
  subJob: AdcmSubJob;
  subJobLogs: AdcmSubJobLogItem[];
}

const ActionWizardOperationLog: React.FC<ActionWizardOperationLogProps> = ({
  subJob,
  subJobLogs,
}: ActionWizardOperationLogProps) => {
  const [currentLogId, setCurrentLogId] = useState<number | null>(null);
  const [isSubJobLogsShown, setIsSubJobLogsShown] = useState(false);

  useEffect(() => {
    if (subJobLogs.length > 0 && !isSubJobLogsShown) {
      setCurrentLogId(subJobLogs[0].id || null);
      setIsSubJobLogsShown(true);
    }
  }, [subJobLogs[0].id]);

  const log = useMemo(() => {
    return subJobLogs.find(({ id }) => currentLogId === id);
  }, [subJobLogs, currentLogId]);

  const onTabChange = (id: number | null) => {
    setCurrentLogId(id);
  };

  return (
    <div className={s.actionWizardOperationLog}>
      {isSubJobLogsShown && (
        <SubJobLogsTabs
          subJobId={subJob?.id}
          subJobLogsList={subJobLogs}
          currentTabId={currentLogId}
          onChangeTab={onTabChange}
        />
      )}

      {!isSubJobLogsShown && (
        <div className={s.actionWizardOperationLog__spinner}>
          <Spinner />
        </div>
      )}

      {subJob && log && <SubJobLog subJob={subJob} subJobLog={log} />}
    </div>
  );
};
export default ActionWizardOperationLog;
