import type React from 'react';
import type { AdcmCluster } from '@models/adcm';
import ClusterCard from '@pages/ClustersPage/ClustersWidget/ClusterCard/ClusterCard';
import s from './ClustersWidgetGrid.module.scss';

export interface ClustersWidgetGridProps {
  clusters: AdcmCluster[];
  selectedClusterId: number | null;
  onSelect: (clusterId: number) => void;
  onUpgrade: (cluster: AdcmCluster) => void;
  onDelete: (cluster: AdcmCluster) => void;
}

const ClustersWidgetGrid: React.FC<ClustersWidgetGridProps> = ({
  clusters,
  selectedClusterId,
  onSelect,
  onUpgrade,
  onDelete,
}) => {
  if (!clusters.length) {
    return <div className={s.clustersWidgetGrid__empty}>No data</div>;
  }

  return (
    <div className={s.clustersWidgetGrid} data-test="clusters-widget-grid">
      {clusters.map((cluster) => (
        <ClusterCard
          key={cluster.id}
          cluster={cluster}
          isSelected={selectedClusterId === cluster.id}
          onSelect={onSelect}
          onUpgrade={onUpgrade}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
};

export default ClustersWidgetGrid;
