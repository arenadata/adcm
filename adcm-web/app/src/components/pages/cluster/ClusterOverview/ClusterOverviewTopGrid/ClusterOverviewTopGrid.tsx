import { useStore } from '@hooks';
import { useParams } from 'react-router-dom';
import { Badge } from '@uikit';
import {
  capitalizeEdition,
  formatCpuVcores,
  formatResourceValue,
} from '@pages/ClustersPage/ClustersWidget/ClustersWidget.utils';
import ClusterOverviewInfoCard from './ClusterOverviewInfoCard';
import ClusterOverviewMetricCard from './ClusterOverviewMetricCard';
import s from './ClusterOverviewTopGrid.module.scss';

const ClusterOverviewTopGrid = () => {
  const { cluster } = useStore((state) => state.adcm.cluster);
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const metrics = useStore((state) => state.adcm.clustersMetrics.metricsByClusterId[clusterId]);

  const version = cluster?.prototype.version;
  const clusterInfoItems = [
    { label: 'Product', value: cluster?.prototype.displayName ?? '—' },
    {
      label: 'Version',
      value: version ? <Badge status="info">{version}</Badge> : '—',
    },
    { label: 'Edition', value: capitalizeEdition(cluster?.prototype.edition) || '—' },
  ];

  const resourceItems = [
    { label: 'CPU', value: formatCpuVcores(metrics?.resources?.cpuVcores) },
    { label: 'RAM', value: formatResourceValue(metrics?.resources?.ram) },
    { label: 'Disk', value: formatResourceValue(metrics?.resources?.disk) },
  ];

  return (
    <div className={s.clusterOverviewTopGrid}>
      <ClusterOverviewInfoCard title="Cluster info" items={clusterInfoItems} />
      <ClusterOverviewInfoCard title="Resources" items={resourceItems} />
      <ClusterOverviewMetricCard title="Services" up={metrics?.services?.up ?? 0} down={metrics?.services?.down ?? 0} />
      <ClusterOverviewMetricCard title="Hosts" up={metrics?.hosts?.up ?? 0} down={metrics?.hosts?.down ?? 0} />
    </div>
  );
};

export default ClusterOverviewTopGrid;
