import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupHosts, getHosts, refreshHosts } from '@store/adcm/hosts/hostsSlice';
import { cleanupRelatedData, loadRelatedData } from '@store/adcm/hosts/hostsTableSlice';

export const useRequestHosts = () => {
  const dispatch = useDispatch();
  const filter = useStore(({ adcm }) => adcm.hostsTable.filter);
  const paginationParams = useStore(({ adcm }) => adcm.hostsTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.hostsTable.requestFrequency);
  const sortParams = useStore(({ adcm }) => adcm.hostsTable.sortParams);

  useEffect(() => {
    dispatch(loadRelatedData());

    return () => {
      dispatch(cleanupHosts);
      dispatch(cleanupRelatedData());
    };
  }, [dispatch]);

  const debounceGetHosts = useDebounce(() => {
    dispatch(getHosts());
  }, defaultDebounceDelay);

  const debounceRefreshHosts = useDebounce(() => {
    dispatch(refreshHosts());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetHosts, debounceRefreshHosts, requestFrequency, [filter, sortParams, paginationParams]);
};
