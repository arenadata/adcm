import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupHosts, getHosts, refreshHosts } from '@store/adcm/hosts/hostsSlice';
import { cleanupRelatedData, loadRelatedData } from '@store/adcm/hosts/hostsTableSlice';
import { cleanupHostDynamicActions, loadHostsDynamicActions } from '@store/adcm/hosts/hostsDynamicActionsSlice';

export const useRequestHosts = () => {
  const dispatch = useDispatch();
  const hosts = useStore(({ adcm }) => adcm.hosts.hosts);
  const filter = useStore(({ adcm }) => adcm.hostsTable.filter);
  const paginationParams = useStore(({ adcm }) => adcm.hostsTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.hostsTable.requestFrequency);
  const sortParams = useStore(({ adcm }) => adcm.hostsTable.sortParams);

  useEffect(() => {
    dispatch(loadRelatedData());

    if (hosts.length) {
      dispatch(loadHostsDynamicActions(hosts));
    }

    return () => {
      dispatch(cleanupHosts);
      dispatch(cleanupHostDynamicActions());
      dispatch(cleanupRelatedData());
    };
  }, [dispatch, hosts]);

  const debounceGetHosts = useDebounce(() => {
    dispatch(getHosts());
  }, defaultDebounceDelay);

  const debounceRefreshHosts = useDebounce(() => {
    dispatch(refreshHosts());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetHosts, debounceRefreshHosts, requestFrequency, [filter, sortParams, paginationParams]);
};
