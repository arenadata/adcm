import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { useEffect } from 'react';
import { defaultDebounceDelay } from '@constants';
import { cleanupList } from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroups/serviceComponentConfigGroupsTableSlice';
import {
  cleanupServiceComponentConfigGroups,
  getServiceComponentConfigGroups,
  refreshServiceComponentConfigGroups,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroups/serviceComponentConfigGroupsSlice';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams';

export const useRequestServiceComponentConfigGroups = () => {
  const dispatch = useDispatch();
  const requestPayload = useServiceComponentParams();
  const sortParams = useStore((s) => s.adcm.serviceComponentConfigGroupsTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.serviceComponentConfigGroupsTable.paginationParams);
  const requestFrequency = useStore((s) => s.adcm.serviceComponentConfigGroupsTable.requestFrequency);

  useEffect(
    () => () => {
      dispatch(cleanupServiceComponentConfigGroups());
      dispatch(cleanupList());
    },
    [dispatch],
  );

  const debounceGetClusterHosts = useDebounce(() => {
    dispatch(getServiceComponentConfigGroups(requestPayload));
  }, defaultDebounceDelay);

  const debounceRefreshClusterHosts = useDebounce(() => {
    dispatch(refreshServiceComponentConfigGroups(requestPayload));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusterHosts, debounceRefreshClusterHosts, requestFrequency, [
    sortParams,
    paginationParams,
  ]);
};
