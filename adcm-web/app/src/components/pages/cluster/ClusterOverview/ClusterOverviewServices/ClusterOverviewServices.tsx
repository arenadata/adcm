import React from 'react';
import PageSection from '@commonComponents/PageSection/PageSection';
import s from './ClusterOverviewServices.module.scss';
import ClusterOverviewDiagram from '@pages/cluster/ClusterOverview/ClusterOverviewDiagram/ClusterOverviewDiagram';
import ClusterOverviewServiceItem from '@pages/cluster/ClusterOverview/ClusterOverviewServices/ClusterOverviewServiceItem/ClusterOverviewServiceItem';
import { Pagination, Spinner } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import ClusterOverviewFilter from '@pages/cluster/ClusterOverview/ClusterOverviewFilter/ClusterOverviewFilter';
import { AdcmClusterStatus } from '@models/adcm';
import { setFilter, setPaginationParams } from '@store/adcm/cluster/overview/overviewServicesTableSlice';
import { PaginationParams } from '@uikit/types/list.types';
import { useParams } from 'react-router-dom';

const ClusterOverviewServices = () => {
  const { servicesStatuses, count, allServicesCount, isLoading } = useStore((s) => s.adcm.clusterOverviewServices);
  const { filter, paginationParams } = useStore((s) => s.adcm.clusterOverviewServicesTable);
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const dispatch = useDispatch();

  const onServicesStatusHandler = (status: AdcmClusterStatus) => {
    dispatch(setFilter({ servicesStatus: status }));
  };

  const onPaginationParamsHandler = (newPaginationParams: PaginationParams) => {
    dispatch(setPaginationParams(newPaginationParams));
  };

  return (
    <PageSection title="Services">
      <div className={s.clusterOverviewServices__wrapper}>
        <ClusterOverviewDiagram totalCount={allServicesCount} currentCount={count} status={filter.servicesStatus} />
        <div className={s.clusterOverviewServices__servicesContainer}>
          <ClusterOverviewFilter
            status={filter.servicesStatus}
            onStatusChange={onServicesStatusHandler}
            dataTest="services-toolbar"
          />
          {isLoading ? (
            <div className={s.clusterOverviewServices__spinnerWrapper}>
              <Spinner />
            </div>
          ) : (
            <div className={s.clusterOverviewServices__services}>
              {servicesStatuses.map((service) => (
                <ClusterOverviewServiceItem clusterId={clusterId} key={service.id} service={service} />
              ))}
              {servicesStatuses.length === 0 && <span className={s.clusterOverviewServices__noData}>No data</span>}
            </div>
          )}
          <div className={s.clusterOverviewServices__footer}>
            <Pagination pageData={paginationParams} totalItems={count} onChangeData={onPaginationParamsHandler} />
          </div>
        </div>
      </div>
    </PageSection>
  );
};

export default ClusterOverviewServices;
