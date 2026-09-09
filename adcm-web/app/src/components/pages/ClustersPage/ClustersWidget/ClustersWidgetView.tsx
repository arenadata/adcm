import { useEffect } from 'react';
import { useCallback } from 'react';
import { useDispatch, useStore } from '@hooks';
import type { AdcmCluster } from '@models/adcm';
import { openDeleteDialog } from '@store/adcm/clusters/clustersActionsSlice';
import { openClusterUpgradeDialog } from '@store/adcm/clusters/clusterUpgradesSlice';
import { setSelectedClusterId } from '@store/adcm/clusters/clustersViewSlice';
import ClustersWidgetGrid from './ClustersWidgetGrid/ClustersWidgetGrid';

const ClustersWidgetView: React.FC = () => {
  const dispatch = useDispatch();
  const clusters = useStore((state) => state.adcm.clusters.clusters);
  const selectedClusterId = useStore((state) => state.adcm.clustersView.selectedClusterId);

  useEffect(() => {
    const firstClusterId = clusters[0]?.id;
    // one find for two cases:
    // * selectedClusterId is existed
    // * in this clusters list already select cluster (after filters selectedClusterId may be not found in new clusters list)
    const isOneClusterAlreadySelected = selectedClusterId && clusters.find(({ id }) => id === selectedClusterId);
    if (firstClusterId && !isOneClusterAlreadySelected) {
      dispatch(setSelectedClusterId(firstClusterId));
    }
  }, [clusters]);

  const handleSelect = useCallback(
    (clusterId: number) => {
      dispatch(setSelectedClusterId(selectedClusterId === clusterId ? null : clusterId));
    },
    [dispatch, selectedClusterId],
  );

  const handleUpgrade = useCallback(
    (cluster: AdcmCluster) => {
      dispatch(openClusterUpgradeDialog(cluster));
    },
    [dispatch],
  );

  const handleDelete = useCallback(
    (cluster: AdcmCluster) => {
      dispatch(openDeleteDialog(cluster));
    },
    [dispatch],
  );

  return (
    <div data-test="clusters-widget-view">
      <ClustersWidgetGrid
        clusters={clusters}
        selectedClusterId={selectedClusterId}
        onSelect={handleSelect}
        onUpgrade={handleUpgrade}
        onDelete={handleDelete}
      />
    </div>
  );
};

export default ClustersWidgetView;
