import React from 'react';
import { TabButton, TabsBlock } from '@uikit';
import { getStatusLabel } from '@utils/humanizationUtils';
import type { AdcmSubJobLogItem } from '@models/adcm';

interface SubJobLogsTabsProps {
  subJobLogsList: AdcmSubJobLogItem[];
  currentTabId: number | null;
  onChangeTab: (id: number) => void;
  className?: string;
}

const SubJobLogsTabs: React.FC<SubJobLogsTabsProps> = ({ subJobLogsList, currentTabId, onChangeTab, className }) => {
  if (subJobLogsList.length === 0) return null;

  return (
    <TabsBlock variant="secondary" className={className}>
      {subJobLogsList.map((subJobLog) => {
        return (
          <TabButton
            isActive={currentTabId === subJobLog.id}
            onClick={() => onChangeTab(subJobLog.id)}
            key={subJobLog.id}
          >
            {getStatusLabel(subJobLog.name)} [{subJobLog.type}]
          </TabButton>
        );
      })}
    </TabsBlock>
  );
};
export default SubJobLogsTabs;
