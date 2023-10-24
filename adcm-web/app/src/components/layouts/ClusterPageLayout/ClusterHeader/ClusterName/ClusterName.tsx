import React from 'react';
import s from './ClusterName.module.scss';
import { useStore } from '@hooks';
import { orElseGet } from '@utils/checkUtils';
import ClusterDynamicActionsIcon from '@pages/ClustersPage/ClustersTable/ClusterDynamicActionsIcon/ClusterDynamicActionsIcon';

const ClusterName: React.FC = () => {
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  return (
    <div className={s.clusterName}>
      <div className={s.clusterName__name}>{orElseGet(cluster?.name)}</div>
      {cluster && <ClusterDynamicActionsIcon cluster={cluster} size={24} />}
    </div>
  );
};
export default ClusterName;
