import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { shallowEqual } from 'react-redux';
import { Pagination, Spinner, WarningMessage } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import ClusterOverviewFilter from '@pages/cluster/ClusterOverview/ClusterOverviewFilter/ClusterOverviewFilter';
import type { ClusterOverviewFilterValue } from '@pages/cluster/ClusterOverview/ClusterOverviewFilter/ClusterOverviewFilter';
import ClusterOverviewServiceItem from '@pages/cluster/ClusterOverview/ClusterOverviewServices/ClusterOverviewServiceItem/ClusterOverviewServiceItem';
import { useRequestClusterServicesOverview } from '@pages/cluster/ClusterOverview/useRequestClusterServicesOverview';
import type { AdcmServiceStatus } from '@models/adcm';
import { setFilter, setPaginationParams } from '@store/adcm/cluster/overview/overviewServicesTableSlice';
import type { PaginationParams } from '@uikit/types/list.types';
import { resetCount } from '@store/adcm/cluster/overview/overviewServicesSlice';
import s from './ClusterOverviewEntities.module.scss';

const ClusterOverviewServicesContent = () => {
  useRequestClusterServicesOverview();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const dispatch = useDispatch();

  const {
    servicesStatuses,
    count,
    isLoading,
    allCount,
    upCount,
    downCount,
    mmCount,
    filter,
    paginationParams,
    servicesCount,
    hasMetrics,
  } = useStore((state) => {
    const metrics = state.adcm.clustersMetrics.metricsByClusterId[clusterId];

    return {
      ...state.adcm.clusterOverviewServices,
      filter: state.adcm.clusterOverviewServicesTable.filter,
      paginationParams: state.adcm.clusterOverviewServicesTable.paginationParams,
      servicesCount: metrics?.services?.count,
      hasMetrics: metrics !== undefined,
    };
  }, shallowEqual);

  const showEmptyServicesNotification = hasMetrics && servicesCount === 0;
  const isContentLoading = isLoading || (!hasMetrics && servicesStatuses.length === 0);
  const counts = useMemo(
    () => ({ all: allCount, up: upCount, down: downCount, mm: mmCount }),
    [allCount, upCount, downCount, mmCount],
  );

  const handleFilterChange = ({ status, maintenanceMode }: ClusterOverviewFilterValue) => {
    dispatch(resetCount());
    dispatch(
      setFilter({
        servicesStatus: status as AdcmServiceStatus | undefined,
        maintenanceMode,
      }),
    );
  };

  const handleNameChange = (name: string) => {
    dispatch(resetCount());
    dispatch(setFilter({ displayName: name || undefined }));
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

    if (showEmptyServicesNotification) {
      return (
        <WarningMessage variant="info" className={s.clusterOverviewEntities__notification}>
          No services have been installed on this cluster yet. You can install them on the{' '}
          <Link to={`/clusters/${clusterId}/services`} className="text-link">
            Services
          </Link>{' '}
          page.
        </WarningMessage>
      );
    }

    return (
      <div className={s.clusterOverviewEntities__services}>
        {servicesStatuses.map((service) => (
          <ClusterOverviewServiceItem clusterId={clusterId} key={service.id} service={service} />
        ))}
        {servicesStatuses.length === 0 && <span className={s.clusterOverviewEntities__noData}>No data</span>}
      </div>
    );
  };

  return (
    <div className={s.clusterOverviewEntities__content}>
      <ClusterOverviewFilter
        status={filter.servicesStatus}
        maintenanceMode={filter.maintenanceMode}
        name={filter.displayName}
        counts={counts}
        onFilterChange={handleFilterChange}
        onNameChange={handleNameChange}
        searchPlaceholder="Search"
        dataTest="services-toolbar"
      />
      {renderContent()}
      <div className={s.clusterOverviewEntities__footer}>
        <Pagination pageData={paginationParams} totalItems={count} onChangeData={handlePaginationParams} />
      </div>
    </div>
  );
};

export default ClusterOverviewServicesContent;
