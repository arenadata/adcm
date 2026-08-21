import { useMemo, useState } from 'react';
import { TabButton, TabsBlock } from '@uikit';
import type { AdcmConcerns } from '@models/adcm';
import ClusterDetailsPanelConcerns from '@pages/ClustersPage/ClustersWidget/ClusterDetailsPanel/ClusterDetailsPanelConcerns';
import s from './ClusterOverviewBottomConcerns.module.scss';

type ClusterOverviewBottomConcernsProps = {
  concerns: AdcmConcerns[];
};

type ConcernsFilterTab = 'all' | 'blocking' | 'nonBlocking';

type ConcernsFilterTabConfig = {
  id: ConcernsFilterTab;
  label: string;
};

const FILTER_TABS: ConcernsFilterTabConfig[] = [
  { id: 'all', label: 'All' },
  { id: 'blocking', label: 'Blocking' },
  { id: 'nonBlocking', label: 'Non-blocking' },
];

const ClusterOverviewBottomConcerns = ({ concerns }: ClusterOverviewBottomConcernsProps) => {
  const [activeTab, setActiveTab] = useState<ConcernsFilterTab>('all');

  const counts = useMemo(
    () => ({
      all: concerns.length,
      blocking: concerns.filter((concern) => concern.isBlocking).length,
      nonBlocking: concerns.filter((concern) => !concern.isBlocking).length,
    }),
    [concerns],
  );

  const filteredConcerns = useMemo(() => {
    if (activeTab === 'blocking') {
      return concerns.filter((concern) => concern.isBlocking);
    }

    if (activeTab === 'nonBlocking') {
      return concerns.filter((concern) => !concern.isBlocking);
    }

    return concerns;
  }, [activeTab, concerns]);

  return (
    <ClusterDetailsPanelConcerns
      concerns={filteredConcerns}
      className={s.clusterOverviewBottomConcerns}
      listClassName={s.clusterOverviewBottomConcerns__list}
      headerSlot={
        <div className={s.clusterOverviewBottomConcerns__header}>
          <h3 className={s.clusterOverviewBottomConcerns__title}>Concerns</h3>
          <TabsBlock variant="secondary" className={s.clusterOverviewBottomConcerns__tabs}>
            {FILTER_TABS.map((tab) => (
              <TabButton key={tab.id} isActive={activeTab === tab.id} onClick={() => setActiveTab(tab.id)}>
                {tab.label} <span className={s.clusterOverviewBottomConcerns__count}>{counts[tab.id]}</span>
              </TabButton>
            ))}
          </TabsBlock>
        </div>
      }
    />
  );
};

export default ClusterOverviewBottomConcerns;
