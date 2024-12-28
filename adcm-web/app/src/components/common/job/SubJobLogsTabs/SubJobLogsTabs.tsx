import type React from 'react';
import { TabButton, TabsBlock } from '@uikit';
import { getStatusLabel } from '@utils/humanizationUtils';
import type { AdcmSubJobLogItem } from '@models/adcm';
import DownloadSubJobLog from '../SubJobLog/DownloadSubJobLog/DownloadSubJobLog';
import s from './SubJobLogsTabs.module.scss';

interface SubJobLogsTabsProps {
  subJobId?: number;
  subJobLogsList: AdcmSubJobLogItem[];
  currentTabId: number | null;
  onChangeTab: (id: number) => void;
  className?: string;
}

const SubJobLogsTabs: React.FC<SubJobLogsTabsProps> = ({
  subJobId,
  subJobLogsList,
  currentTabId,
  onChangeTab,
  className,
}) => {
  if (subJobLogsList.length === 0) return null;

  return (
    <TabsBlock variant="secondary" className={className}>
      {subJobLogsList.map((subJobLog) => {
        const isActive = currentTabId === subJobLog.id;
        return (
          <TabButton
            className={s.tabButton}
            isActive={isActive}
            onClick={() => onChangeTab(subJobLog.id)}
            key={subJobLog.id}
          >
            {isActive && subJobId && <DownloadSubJobLog subJobId={subJobId} subJobLogId={currentTabId} />}
            {getStatusLabel(subJobLog.name)} [{subJobLog.type}]
          </TabButton>
        );
      })}
    </TabsBlock>
  );
};
export default SubJobLogsTabs;
