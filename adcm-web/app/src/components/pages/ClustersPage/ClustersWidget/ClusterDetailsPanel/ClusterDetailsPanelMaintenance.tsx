import type React from 'react';
import { memo, useCallback, useMemo, useState } from 'react';
import { EMPTY_ARRAY } from '@constants';
import { Link } from 'react-router-dom';
import { TabsBlock, TabButton, VirtualList } from '@uikit';
import type { MaintenanceEntityItem } from './useClusterMaintenanceMode';
import s from './ClusterDetailsPanel.module.scss';

type MaintenanceEntity = 'services' | 'hosts';

const MM_ITEM_SIZE = 22;
const MM_LIST_GAP = 6;

export interface ClusterDetailsPanelMaintenanceProps {
  clusterId: number;
  services: MaintenanceEntityItem[];
  hosts: MaintenanceEntityItem[];
  servicesCount: number;
  hostsCount: number;
}

type MaintenanceListItemProps = {
  clusterId: number;
  entity: MaintenanceEntity;
  item: MaintenanceEntityItem;
};

const MaintenanceListItem = memo(({ clusterId, entity, item }: MaintenanceListItemProps) => (
  <Link className={s.clusterDetailsPanel__mmItem} to={`/clusters/${clusterId}/${entity}/${item.id}`}>
    {item.name}
  </Link>
));

MaintenanceListItem.displayName = 'MaintenanceListItem';

const ClusterDetailsPanelMaintenance: React.FC<ClusterDetailsPanelMaintenanceProps> = ({
  clusterId,
  services,
  hosts,
  servicesCount,
  hostsCount,
}) => {
  const [entity, setEntity] = useState<MaintenanceEntity>(servicesCount > 0 ? 'services' : 'hosts');
  const items = useMemo(() => (entity === 'services' ? services : hosts), [entity, services, hosts]);
  const count = entity === 'services' ? servicesCount : hostsCount;
  const listItems = useMemo(() => (count === 0 ? EMPTY_ARRAY : items), [count, items]);
  const renderItem = useCallback(
    (item: MaintenanceEntityItem) => <MaintenanceListItem clusterId={clusterId} entity={entity} item={item} />,
    [clusterId, entity],
  );

  return (
    <div className={s.clusterDetailsPanel__card}>
      <div className={s.clusterDetailsPanel__sectionHeader}>
        <span className={s.clusterDetailsPanel__sectionTitle}>Maintenance mode</span>
        <TabsBlock variant="secondary" className={s.clusterDetailsPanel__tabs}>
          <TabButton isActive={entity === 'services'} onClick={() => setEntity('services')}>
            Services {servicesCount}
          </TabButton>
          <TabButton isActive={entity === 'hosts'} onClick={() => setEntity('hosts')}>
            Hosts {hostsCount}
          </TabButton>
        </TabsBlock>
      </div>

      <VirtualList
        key={entity}
        items={listItems}
        className={s.clusterDetailsPanel__mmList}
        getItemKey={(item) => item.id}
        estimateSize={MM_ITEM_SIZE}
        gap={MM_LIST_GAP}
        emptyContent={<div className={s.clusterDetailsPanel__empty}>No data</div>}
        renderItem={renderItem}
      />
    </div>
  );
};

export default ClusterDetailsPanelMaintenance;
