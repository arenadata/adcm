import type React from 'react';
import { TabsBlock, TabButton } from '@uikit';

export type JobViewMode = 'table' | 'graph';

export interface JobViewToggleProps {
  viewMode: JobViewMode;
  onChange: (viewMode: JobViewMode) => void;
}

const JobViewToggle: React.FC<JobViewToggleProps> = ({ viewMode, onChange }) => {
  return (
    <TabsBlock variant="secondary" dataTest="job-view-toggle">
      <TabButton isActive={viewMode === 'table'} onClick={() => onChange('table')}>
        Table view
      </TabButton>
      <TabButton isActive={viewMode === 'graph'} onClick={() => onChange('graph')}>
        Graph view
      </TabButton>
    </TabsBlock>
  );
};

export default JobViewToggle;
