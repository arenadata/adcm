import React, { useMemo } from 'react';
import PageSection from '@commonComponents/PageSection/PageSection';
import s from './ClusterOverviewHosts.module.scss';
import ClusterOverviewDiagram from '@pages/cluster/ClusterOverview/ClusterOverviewDiagram/ClusterOverviewDiagram';
import { Pagination, Spinner } from '@uikit';
import ClusterOverviewFilter from '@pages/cluster/ClusterOverview/ClusterOverviewFilter/ClusterOverviewFilter';
import { useDispatch, useStore } from '@hooks';
import { AdcmClusterStatus } from '@models/adcm';
import { setFilter, setPaginationParams } from '@store/adcm/cluster/overview/overviewHostsTableSlice';
import { PaginationParams } from '@uikit/types/list.types';
import ClusterOverviewHostsTable from '@pages/cluster/ClusterOverview/ClusterOverviewHosts/ClusterOverviewHostsTable';

const ClusterOverviewHosts = () => {
  const { hostsStatuses, count, allHostsCount, isLoading } = useStore((s) => s.adcm.clusterOverviewHosts);
  const { filter, paginationParams } = useStore((s) => s.adcm.clusterOverviewHostsTable);
  const dispatch = useDispatch();

  const onHostsStatusHandler = (status: AdcmClusterStatus) => {
    dispatch(setFilter({ hostsStatus: status }));
  };

  const onPaginationParamsHandler = (newPaginationParams: PaginationParams) => {
    dispatch(setPaginationParams(newPaginationParams));
  };

  const firstHostsGroup = useMemo(() => hostsStatuses.filter((item, id) => id % 2 === 0), [hostsStatuses]);
  const secondHostsGroup = useMemo(() => hostsStatuses.filter((item, id) => id % 2 !== 0), [hostsStatuses]);

  return (
    <PageSection title="Hosts">
      <div className={s.clusterOverviewHosts__wrapper}>
        <ClusterOverviewDiagram totalCount={allHostsCount} currentCount={count} status={filter.hostsStatus} />
        <div className={s.clusterOverviewHosts__hostsContainer}>
          <ClusterOverviewFilter
            status={filter.hostsStatus}
            onStatusChange={onHostsStatusHandler}
            dataTest="hosts-toolbar"
          />
          {isLoading ? (
            <div className={s.clusterOverviewHosts__spinnerWrapper}>
              <Spinner />
            </div>
          ) : (
            <div className={s.clusterOverviewHosts__hosts}>
              {firstHostsGroup.length > 0 && <ClusterOverviewHostsTable hosts={firstHostsGroup} />}
              {secondHostsGroup.length > 0 && <ClusterOverviewHostsTable hosts={secondHostsGroup} />}
              {firstHostsGroup.length + secondHostsGroup.length === 0 && (
                <span className={s.clusterOverviewHosts__noData}>No Data</span>
              )}
            </div>
          )}
          <div className={s.clusterOverviewHosts__footer}>
            <Pagination pageData={paginationParams} totalItems={count} onChangeData={onPaginationParamsHandler} />
          </div>
        </div>
      </div>
    </PageSection>
  );
};

export default ClusterOverviewHosts;
