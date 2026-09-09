import type React from 'react';
import type { AdcmCluster, AdcmClusterMetrics } from '@models/adcm';
import ClusterDetailsPanelHeader from './ClusterDetailsPanelHeader';
import ClusterDetailsPanelMetrics from './ClusterDetailsPanelMetrics';
import ClusterDetailsPanelConcerns from './ClusterDetailsPanelConcerns';
import ClusterDetailsPanelMaintenance from './ClusterDetailsPanelMaintenance';
import ClusterContractVersionWarning from '@commonComponents/ClusterContractVersionWarning/ClusterContractVersionWarning';
import { useClusterMaintenanceMode } from './useClusterMaintenanceMode';
import { useRequestClusterMaintenanceMode } from './useRequestClusterMaintenanceMode';
import s from './ClusterDetailsPanel.module.scss';

export interface ClusterDetailsPanelProps {
  cluster: AdcmCluster;
  metrics?: AdcmClusterMetrics;
}

const ClusterDetailsPanel: React.FC<ClusterDetailsPanelProps> = ({ cluster, metrics }) => {
  useRequestClusterMaintenanceMode(cluster.id);
  const { services, hosts, servicesCount, hostsCount, hasMaintenanceMode } = useClusterMaintenanceMode(cluster.id);

  return (
    <aside className={s.clusterDetailsPanel} data-test="cluster-details-panel">
      <ClusterDetailsPanelHeader cluster={cluster} />

      <ClusterContractVersionWarning cluster={cluster} className={s.clusterDetailsPanel__warning} />

      <ClusterDetailsPanelMetrics metrics={metrics} />

      {cluster.concerns.length > 0 ? (
        <ClusterDetailsPanelConcerns concerns={cluster.concerns} />
      ) : (
        <div className={s.clusterDetailsPanel__card}>
          <span className={s.clusterDetailsPanel__empty}>The cluster has no issues</span>
        </div>
      )}

      {hasMaintenanceMode && (
        <ClusterDetailsPanelMaintenance
          clusterId={cluster.id}
          services={services}
          hosts={hosts}
          servicesCount={servicesCount}
          hostsCount={hostsCount}
        />
      )}
    </aside>
  );
};

export default ClusterDetailsPanel;
