import { useMemo } from 'react';
import PageSection from '@commonComponents/PageSection/PageSection';
import s from './ClusterOverviewHosts.module.scss';
import ClusterOverviewDiagram from '@pages/cluster/ClusterOverview/ClusterOverviewDiagram/ClusterOverviewDiagram';
import { Pagination, Spinner } from '@uikit';
import ClusterOverviewFilter from '@pages/cluster/ClusterOverview/ClusterOverviewFilter/ClusterOverviewFilter';
import { useDispatch, useStore } from '@hooks';
import type { AdcmHostStatus, AdcmServiceStatus } from '@models/adcm';
import { setFilter, setPaginationParams } from '@store/adcm/cluster/overview/overviewHostsTableSlice';
import type { PaginationParams } from '@uikit/types/list.types';
import ClusterOverviewHostsTable from '@pages/cluster/ClusterOverview/ClusterOverviewHosts/ClusterOverviewHostsTable';
import { resetCount } from '@store/adcm/cluster/overview/overviewHostsSlice';

const ClusterOverviewHosts = () => {
  const { hostsStatuses, count, upCount, downCount, isLoading } = useStore((s) => s.adcm.clusterOverviewHosts);
  const { filter, paginationParams } = useStore((s) => s.adcm.clusterOverviewHostsTable);
  const dispatch = useDispatch();

  const onHostsStatusHandler = (status?: AdcmHostStatus | AdcmServiceStatus) => {
    dispatch(resetCount());
    dispatch(setFilter({ hostsStatus: status as AdcmHostStatus }));
  };

  const onPaginationParamsHandler = (newPaginationParams: PaginationParams) => {
    dispatch(setPaginationParams(newPaginationParams));
  };

  const firstHostsGroup = useMemo(() => hostsStatuses.filter((_item, id) => id % 2 === 0), [hostsStatuses]);
  const secondHostsGroup = useMemo(() => hostsStatuses.filter((_item, id) => id % 2 !== 0), [hostsStatuses]);

  const currentCount = useMemo(() => (!filter.hostsStatus ? upCount : count), [upCount, count, filter.hostsStatus]);

  const allCount = useMemo(
    () => (!filter.hostsStatus ? downCount : downCount + upCount),
    [downCount, upCount, filter.hostsStatus],
  );

  return (
    <PageSection title="Hosts">
      <div className={s.clusterOverviewHosts__wrapper}>
        <ClusterOverviewDiagram totalCount={allCount} currentCount={currentCount} status={filter.hostsStatus} />
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
                <span className={s.clusterOverviewHosts__noData}>No data</span>
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
