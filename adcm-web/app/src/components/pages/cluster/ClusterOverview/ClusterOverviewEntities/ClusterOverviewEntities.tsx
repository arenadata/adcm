import { useState } from 'react';
import { TabButton, TabsBlock } from '@uikit';
import ClusterOverviewServicesContent from './ClusterOverviewServicesContent';
import ClusterOverviewHostsContent from './ClusterOverviewHostsContent';
import s from './ClusterOverviewEntities.module.scss';

type OverviewEntity = 'services' | 'hosts';

const ClusterOverviewEntities = () => {
  const [entity, setEntity] = useState<OverviewEntity>('services');

  return (
    <section className={s.clusterOverviewEntities}>
      <div className={s.clusterOverviewEntities__header}>
        <TabsBlock className={s.clusterOverviewEntities__tabs}>
          <TabButton
            className={s.clusterOverviewEntities__tabsButton}
            isActive={entity === 'services'}
            onClick={() => setEntity('services')}
          >
            Services
          </TabButton>
          <TabButton
            className={s.clusterOverviewEntities__tabsButton}
            isActive={entity === 'hosts'}
            onClick={() => setEntity('hosts')}
          >
            Hosts
          </TabButton>
        </TabsBlock>
      </div>
      {entity === 'services' ? <ClusterOverviewServicesContent /> : <ClusterOverviewHostsContent />}
    </section>
  );
};

export default ClusterOverviewEntities;
