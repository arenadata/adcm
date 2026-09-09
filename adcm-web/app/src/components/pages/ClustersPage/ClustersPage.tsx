import ClustersTableToolbar from './ClustersTableToolbar/ClustersTableToolbar';
import ClustersTable from './ClustersTable/ClustersTable';
import ClustersTableFooter from './ClustersTableFooter/ClustersTableFooter';
import ClustersWidgetView from './ClustersWidget/ClustersWidgetView';
import ClusterDetailsPanel from './ClustersWidget/ClusterDetailsPanel/ClusterDetailsPanel';
import ClustersViewToggle from './ClustersViewToggle/ClustersViewToggle';
import ClustersEmptyInfoBanner from './ClustersEmptyInfoBanner/ClustersEmptyInfoBanner';
import Dialogs from './Dialogs';
import { useRequestClusters } from './useRequestClusters';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import { useDispatch, useStore } from '@hooks';
import { setViewMode, type ClustersViewMode } from '@store/adcm/clusters/clustersViewSlice';
import { LoadState } from '@models/loadState';
import s from './ClustersPage.module.scss';

const ClustersPage = () => {
  useRequestClusters();
  const dispatch = useDispatch();
  const viewMode = useStore((state) => state.adcm.clustersView.viewMode);
  const clusters = useStore((state) => state.adcm.clusters.clusters);
  const totalCount = useStore((state) => state.adcm.clusters.totalCount);
  const loadState = useStore((state) => state.adcm.clusters.loadState);
  const filter = useStore((state) => state.adcm.clustersTable.filter);
  const selectedClusterId = useStore((state) => state.adcm.clustersView.selectedClusterId);
  const selectedClusterMetrics = useStore((state) =>
    selectedClusterId ? state.adcm.clustersMetrics.metricsByClusterId[selectedClusterId] : undefined,
  );

  const hasActiveFilters = Boolean(filter.name || filter.status || filter.prototypeDisplayName);
  const showEmptyClustersNotification = loadState === LoadState.Loaded && totalCount === 0 && !hasActiveFilters;

  const selectedCluster =
    viewMode === 'widget' ? (clusters.find((cluster) => cluster.id === selectedClusterId) ?? null) : null;

  const handleViewModeChange = (nextViewMode: ClustersViewMode) => {
    dispatch(setViewMode(nextViewMode));
  };

  return (
    <>
      <TableContainer className={s.clustersPage} variant="easy">
        <ClustersViewToggle viewMode={viewMode} onChange={handleViewModeChange} />
        {showEmptyClustersNotification && <ClustersEmptyInfoBanner />}
        <div className={s.clustersPage__content}>
          <div className={s.clustersPage__main}>
            <ClustersTableToolbar />
            {viewMode === 'table' ? <ClustersTable /> : <ClustersWidgetView />}
            <ClustersTableFooter />
          </div>
          {selectedCluster && <ClusterDetailsPanel cluster={selectedCluster} metrics={selectedClusterMetrics} />}
        </div>
      </TableContainer>
      <Dialogs />
    </>
  );
};

export default ClustersPage;
