import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { useParams } from 'react-router-dom';
import { useEffect } from 'react';
import {
  cleanupClusterConfigGroups,
  getClusterConfigGroups,
  refreshClusterConfigGroups,
} from '@store/adcm/cluster/configGroups/clusterConfigGroupsSlice';
import { defaultDebounceDelay } from '@constants';
import { cleanupList } from '@store/adcm/cluster/configGroups/clusterConfigGroupsTableSlice';

export const useRequestClusterConfigGroups = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const sortParams = useStore((s) => s.adcm.clusterConfigGroupsTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.clusterConfigGroupsTable.paginationParams);
  const requestFrequency = useStore((s) => s.adcm.clusterConfigGroupsTable.requestFrequency);

  useEffect(
    () => () => {
      dispatch(cleanupClusterConfigGroups());
      dispatch(cleanupList());
    },
    [dispatch],
  );

  const debounceGetClusterHosts = useDebounce(() => {
    dispatch(getClusterConfigGroups(clusterId));
  }, defaultDebounceDelay);

  const debounceRefreshClusterHosts = useDebounce(() => {
    dispatch(refreshClusterConfigGroups(clusterId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusterHosts, debounceRefreshClusterHosts, requestFrequency, [
    sortParams,
    paginationParams,
  ]);
};
