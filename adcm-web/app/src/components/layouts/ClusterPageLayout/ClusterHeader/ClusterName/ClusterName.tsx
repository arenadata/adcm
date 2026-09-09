import type React from 'react';
import s from './ClusterName.module.scss';
import { useStore } from '@hooks';
import ClusterDynamicActionsIcon from '@pages/ClustersPage/ClustersTable/ClusterDynamicActionsIcon/ClusterDynamicActionsIcon';
import Statusable from '@uikit/Statusable/Statusable';
import { clusterStatusesMap } from '@pages/ClustersPage/ClustersTable/ClustersTable.constants';

const ClusterName: React.FC = () => {
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  if (!cluster) {
    return null;
  }

  return (
    <div className={s.clusterName}>
      <ClusterDynamicActionsIcon cluster={cluster} size={24} />
      <Statusable
        className={s.clusterName__status}
        status={clusterStatusesMap[cluster.status]}
        size="medium"
        iconPosition="right"
      >
        <span className={s.clusterName__title}>{cluster.name}</span>
      </Statusable>
    </div>
  );
};

export default ClusterName;
