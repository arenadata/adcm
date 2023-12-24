import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { useParams } from 'react-router-dom';
import { useEffect } from 'react';
import { defaultDebounceDelay } from '@constants';
import { cleanupList } from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsTableSlice';
import {
  cleanupClusterServiceConfigGroups,
  getClusterServiceConfigGroups,
  refreshClusterServiceConfigGroups,
} from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsSlice';

export const useRequestServiceConfigGroups = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl, serviceId: serviceIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const serviceId = Number(serviceIdFromUrl);
  const requestPayload = { clusterId, serviceId };
  const sortParams = useStore((s) => s.adcm.serviceConfigGroupsTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.serviceConfigGroupsTable.paginationParams);
  const requestFrequency = useStore((s) => s.adcm.serviceConfigGroupsTable.requestFrequency);

  useEffect(
    () => () => {
      dispatch(cleanupClusterServiceConfigGroups());
      dispatch(cleanupList());
    },
    [dispatch],
  );

  const debounceGetClusterHosts = useDebounce(() => {
    dispatch(getClusterServiceConfigGroups(requestPayload));
  }, defaultDebounceDelay);

  const debounceRefreshClusterHosts = useDebounce(() => {
    dispatch(refreshClusterServiceConfigGroups(requestPayload));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusterHosts, debounceRefreshClusterHosts, requestFrequency, [
    sortParams,
    paginationParams,
  ]);
};
