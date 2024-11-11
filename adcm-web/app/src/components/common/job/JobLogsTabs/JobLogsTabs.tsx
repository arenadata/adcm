import React from 'react';
import { TabButton, TabsBlock } from '@uikit';
import { getStatusLabel } from '@utils/humanizationUtils';
import type { AdcmJobLogItem } from '@models/adcm';

interface JobLogsTabsProps {
  jobLogsList: AdcmJobLogItem[];
  currentTabId: number | null;
  onChangeTab: (id: number) => void;
  className?: string;
}

const JobLogsTabs: React.FC<JobLogsTabsProps> = ({ jobLogsList, currentTabId, onChangeTab, className }) => {
  if (jobLogsList.length === 0) return null;

  return (
    <TabsBlock variant="secondary" className={className}>
      {jobLogsList.map((jobLog) => {
        return (
          <TabButton isActive={currentTabId === jobLog.id} onClick={() => onChangeTab(jobLog.id)} key={jobLog.id}>
            {getStatusLabel(jobLog.name)} [{jobLog.type}]
          </TabButton>
        );
      })}
    </TabsBlock>
  );
};
export default JobLogsTabs;
