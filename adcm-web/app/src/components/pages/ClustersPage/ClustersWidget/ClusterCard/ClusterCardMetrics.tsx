import type React from 'react';
import type { AdcmClusterMetrics } from '@models/adcm';
import type { ClusterCardMetricTooltip } from './ClusterCardMetric';
import { formatCpuVcores, formatResourceValue } from '@pages/ClustersPage/ClustersWidget/ClustersWidget.utils';
import ClusterCardMetric from './ClusterCardMetric';
import s from './ClusterCard.module.scss';

const METRICS_UPDATE_TOOLTIP = 'This data is updated once daily';

const maintenanceTooltip: ClusterCardMetricTooltip = {
  label: 'Maintenance mode',
  icon: 'g1-maintenance',
  iconClassName: s.clusterCard__metricIcon_mm,
};

const resourceTooltip: ClusterCardMetricTooltip = {
  label: METRICS_UPDATE_TOOLTIP,
  icon: 'g1-info',
  iconClassName: s.clusterCard__metricIcon,
};

export interface ClusterCardMetricsProps {
  metrics?: AdcmClusterMetrics;
}

const ClusterCardMetrics: React.FC<ClusterCardMetricsProps> = ({ metrics }) => {
  const entityMetrics = [
    {
      label: 'Services',
      value: metrics?.services?.count ?? '—',
      tooltip: (metrics?.services?.maintenanceMode ?? 0) > 0 ? maintenanceTooltip : undefined,
    },
    {
      label: 'Hosts',
      value: metrics?.hosts?.count ?? '—',
      tooltip: (metrics?.hosts?.maintenanceMode ?? 0) > 0 ? maintenanceTooltip : undefined,
    },
  ];

  const resourceMetrics = [
    { label: 'CPU', value: formatCpuVcores(metrics?.resources?.cpuVcores) },
    { label: 'RAM', value: formatResourceValue(metrics?.resources?.ram) },
    { label: 'Disk', value: formatResourceValue(metrics?.resources?.disk) },
  ];

  return (
    <div className={s.clusterCard__metrics}>
      <div className={s.clusterCard__metricsRow}>
        {entityMetrics.map((metric) => (
          <ClusterCardMetric key={metric.label} {...metric} />
        ))}
      </div>
      <div className={s.clusterCard__metricsRow}>
        {resourceMetrics.map((metric) => (
          <ClusterCardMetric key={metric.label} {...metric} tooltip={resourceTooltip} />
        ))}
      </div>
    </div>
  );
};

export default ClusterCardMetrics;
