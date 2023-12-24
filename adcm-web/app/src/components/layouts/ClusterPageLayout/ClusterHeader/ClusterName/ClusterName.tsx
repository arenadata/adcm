import React from 'react';
import s from './ClusterName.module.scss';
import { useStore } from '@hooks';
import ClusterDynamicActionsIcon from '@pages/ClustersPage/ClustersTable/ClusterDynamicActionsIcon/ClusterDynamicActionsIcon';
import Statusable from '@uikit/Statusable/Statusable';
import { clusterStatusesMap } from '@pages/ClustersPage/ClustersTable/ClustersTable.constants';

const ClusterName: React.FC = () => {
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  return (
    <div className={s.clusterName}>
      {cluster && <ClusterDynamicActionsIcon cluster={cluster} size={24} />}
      <div className={s.clusterName__name}>
        {cluster && (
          <Statusable status={clusterStatusesMap[cluster.status]} size="medium">
            {cluster?.name}
          </Statusable>
        )}
      </div>
    </div>
  );
};
export default ClusterName;
