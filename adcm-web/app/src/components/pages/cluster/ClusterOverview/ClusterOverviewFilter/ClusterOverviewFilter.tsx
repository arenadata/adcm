import type React from 'react';
import { defaultDebounceDelay } from '@constants';
import { TabsBlock, TabButton, SearchInput } from '@uikit';
import type { AdcmHostStatus } from '@models/adcm';
import { AdcmMaintenanceMode, AdcmServiceStatus } from '@models/adcm';
import s from './ClusterOverviewFilter.module.scss';

export type ClusterOverviewFilterTab = 'all' | 'up' | 'down' | 'mm';

export type ClusterOverviewFilterCounts = Record<ClusterOverviewFilterTab, number>;

export type ClusterOverviewFilterValue = {
  status?: AdcmServiceStatus | AdcmHostStatus;
  maintenanceMode?: AdcmMaintenanceMode;
};

type ClusterOverviewFilterTabConfig = {
  id: ClusterOverviewFilterTab;
  label: string;
  value: ClusterOverviewFilterValue;
};

const FILTER_TABS: ClusterOverviewFilterTabConfig[] = [
  { id: 'all', label: 'All', value: { status: undefined, maintenanceMode: undefined } },
  { id: 'up', label: 'Up', value: { status: AdcmServiceStatus.Up, maintenanceMode: undefined } },
  { id: 'down', label: 'Down', value: { status: AdcmServiceStatus.Down, maintenanceMode: undefined } },
  { id: 'mm', label: 'Maintenance mode', value: { status: undefined, maintenanceMode: AdcmMaintenanceMode.On } },
];

const getActiveTab = ({ status, maintenanceMode }: ClusterOverviewFilterValue): ClusterOverviewFilterTab => {
  const activeTab = FILTER_TABS.find(
    (tab) => tab.value.status === status && tab.value.maintenanceMode === maintenanceMode,
  );

  return activeTab?.id ?? 'all';
};

interface ClusterOverviewFilterProps {
  status?: AdcmServiceStatus | AdcmHostStatus;
  maintenanceMode?: AdcmMaintenanceMode;
  name?: string;
  counts: ClusterOverviewFilterCounts;
  onFilterChange: (value: ClusterOverviewFilterValue) => void;
  onNameChange: (name: string) => void;
  searchPlaceholder?: string;
  dataTest?: string;
}

const ClusterOverviewFilter = ({
  status,
  maintenanceMode,
  name = '',
  counts,
  onFilterChange,
  onNameChange,
  searchPlaceholder = 'Search',
  dataTest,
}: ClusterOverviewFilterProps) => {
  const activeTab = getActiveTab({ status, maintenanceMode });

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onNameChange(event.target.value);
  };

  return (
    <div className={s.clusterOverviewFilter} data-test={dataTest}>
      <TabsBlock variant="secondary" className={s.clusterOverviewFilter__tabs}>
        {FILTER_TABS.map((tab) => (
          <TabButton key={tab.id} isActive={activeTab === tab.id} onClick={() => onFilterChange(tab.value)}>
            {tab.label} <span className={s.clusterOverviewFilter__count}>{counts[tab.id]}</span>
          </TabButton>
        ))}
      </TabsBlock>

      <SearchInput
        className={s.clusterOverviewFilter__search}
        placeholder={searchPlaceholder}
        value={name}
        variant="primary"
        debounceDelay={defaultDebounceDelay}
        onChange={handleNameChange}
      />
    </div>
  );
};

export default ClusterOverviewFilter;
