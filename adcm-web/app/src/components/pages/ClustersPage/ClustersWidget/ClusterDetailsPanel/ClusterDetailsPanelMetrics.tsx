import type { AdcmClusterMetrics } from '@models/adcm';
import ClusterEntityMetricCard from '@commonComponents/ClusterEntityMetricCard/ClusterEntityMetricCard';
import s from './ClusterDetailsPanel.module.scss';

export interface ClusterDetailsPanelMetricsProps {
  metrics?: AdcmClusterMetrics;
}

const ClusterDetailsPanelMetrics: React.FC<ClusterDetailsPanelMetricsProps> = ({ metrics }) => (
  <div className={s.clusterDetailsPanel__metrics}>
    <ClusterEntityMetricCard
      className={s.clusterDetailsPanel__metricCard}
      title="Services"
      up={metrics?.services?.up ?? 0}
      down={metrics?.services?.down ?? 0}
    />
    <ClusterEntityMetricCard
      className={s.clusterDetailsPanel__metricCard}
      title="Hosts"
      up={metrics?.hosts?.up ?? 0}
      down={metrics?.hosts?.down ?? 0}
    />
  </div>
);

export default ClusterDetailsPanelMetrics;
