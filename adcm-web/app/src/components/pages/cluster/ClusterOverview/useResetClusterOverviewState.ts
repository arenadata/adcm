import { useLayoutEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch } from '@hooks';
import { cleanupList as cleanupServicesTable } from '@store/adcm/cluster/overview/overviewServicesTableSlice';
import { cleanupList as cleanupHostsTable } from '@store/adcm/cluster/overview/overviewHostsTableSlice';
import { cleanupClusterServicesStatuses } from '@store/adcm/cluster/overview/overviewServicesSlice';
import { cleanupClusterHostsStatuses } from '@store/adcm/cluster/overview/overviewHostsSlice';

export const useResetClusterOverviewState = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  useLayoutEffect(() => {
    if (!clusterId) {
      return;
    }

    dispatch(cleanupServicesTable());
    dispatch(cleanupHostsTable());
    dispatch(cleanupClusterServicesStatuses());
    dispatch(cleanupClusterHostsStatuses());
  }, [clusterId, dispatch]);
};
