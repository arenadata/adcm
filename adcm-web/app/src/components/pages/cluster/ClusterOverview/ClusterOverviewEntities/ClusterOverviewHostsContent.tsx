import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { shallowEqual } from 'react-redux';
import { Pagination, Spinner, WarningMessage } from '@uikit';
import ClusterOverviewFilter from '@pages/cluster/ClusterOverview/ClusterOverviewFilter/ClusterOverviewFilter';
import type { ClusterOverviewFilterValue } from '@pages/cluster/ClusterOverview/ClusterOverviewFilter/ClusterOverviewFilter';
import { useDispatch, useStore } from '@hooks';
import { useRequestClusterHostsOverview } from '@pages/cluster/ClusterOverview/useRequestClusterHostsOverview';
import type { AdcmHostStatus } from '@models/adcm';
import { setFilter, setPaginationParams } from '@store/adcm/cluster/overview/overviewHostsTableSlice';
import type { PaginationParams } from '@uikit/types/list.types';
import ClusterOverviewHostItem from '@pages/cluster/ClusterOverview/ClusterOverviewHosts/ClusterOverviewHostItem/ClusterOverviewHostItem';
import { resetCount } from '@store/adcm/cluster/overview/overviewHostsSlice';
import s from './ClusterOverviewEntities.module.scss';

const ClusterOverviewHostsContent = () => {
  useRequestClusterHostsOverview();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const dispatch = useDispatch();

  const {
    hostsStatuses,
    count,
    isLoading,
    allCount,
    upCount,
    downCount,
    mmCount,
    filter,
    paginationParams,
    hostsCount,
    hasMetrics,
  } = useStore((state) => {
    const metrics = state.adcm.clustersMetrics.metricsByClusterId[clusterId];

    return {
      ...state.adcm.clusterOverviewHosts,
      filter: state.adcm.clusterOverviewHostsTable.filter,
      paginationParams: state.adcm.clusterOverviewHostsTable.paginationParams,
      hostsCount: metrics?.hosts?.count,
      hasMetrics: metrics !== undefined,
    };
  }, shallowEqual);

  const showEmptyHostsNotification = hasMetrics && hostsCount === 0;
  const isContentLoading = isLoading || (!hasMetrics && hostsStatuses.length === 0);
  const counts = useMemo(
    () => ({ all: allCount, up: upCount, down: downCount, mm: mmCount }),
    [allCount, upCount, downCount, mmCount],
  );

  const handleFilterChange = ({ status, maintenanceMode }: ClusterOverviewFilterValue) => {
    dispatch(resetCount());
    dispatch(
      setFilter({
        hostsStatus: status as AdcmHostStatus | undefined,
        maintenanceMode,
      }),
    );
  };

  const handleNameChange = (name: string) => {
    dispatch(resetCount());
    dispatch(setFilter({ name: name || undefined }));
  };

  const handlePaginationParams = (newPaginationParams: PaginationParams) => {
    dispatch(setPaginationParams(newPaginationParams));
  };

  const renderContent = () => {
    if (isContentLoading) {
      return (
        <div className={s.clusterOverviewEntities__spinnerWrapper}>
          <Spinner />
        </div>
      );
    }

    if (showEmptyHostsNotification) {
      return (
        <WarningMessage variant="info" className={s.clusterOverviewEntities__notification}>
          No hosts have been added to this cluster yet. You can add them on the{' '}
          <Link to={`/clusters/${clusterId}/hosts`} className="text-link">
            Hosts
          </Link>{' '}
          page.
        </WarningMessage>
      );
    }

    return (
      <div className={s.clusterOverviewEntities__hosts}>
        {hostsStatuses.map((host) => (
          <ClusterOverviewHostItem key={host.id} host={host} clusterId={clusterId} />
        ))}
        {hostsStatuses.length === 0 && <span className={s.clusterOverviewEntities__noData}>No data</span>}
      </div>
    );
  };

  return (
    <div className={s.clusterOverviewEntities__content}>
      <ClusterOverviewFilter
        status={filter.hostsStatus}
        maintenanceMode={filter.maintenanceMode}
        name={filter.name}
        counts={counts}
        onFilterChange={handleFilterChange}
        onNameChange={handleNameChange}
        searchPlaceholder="Search"
        dataTest="hosts-toolbar"
      />
      {renderContent()}
      <div className={s.clusterOverviewEntities__footer}>
        <Pagination pageData={paginationParams} totalItems={count} onChangeData={handlePaginationParams} />
      </div>
    </div>
  );
};

export default ClusterOverviewHostsContent;
