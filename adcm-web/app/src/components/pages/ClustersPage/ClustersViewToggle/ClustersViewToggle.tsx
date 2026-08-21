import type React from 'react';
import { TabsBlock, TabButton } from '@uikit';
import type { ClustersViewMode } from '@store/adcm/clusters/clustersViewSlice';

export interface ClustersViewToggleProps {
  viewMode: ClustersViewMode;
  onChange: (viewMode: ClustersViewMode) => void;
}

const ClustersViewToggle: React.FC<ClustersViewToggleProps> = ({ viewMode, onChange }) => {
  return (
    <TabsBlock variant="secondary" dataTest="clusters-view-toggle">
      <TabButton isActive={viewMode === 'table'} onClick={() => onChange('table')}>
        Table view
      </TabButton>
      <TabButton isActive={viewMode === 'widget'} onClick={() => onChange('widget')}>
        Widget view
      </TabButton>
    </TabsBlock>
  );
};

export default ClustersViewToggle;
