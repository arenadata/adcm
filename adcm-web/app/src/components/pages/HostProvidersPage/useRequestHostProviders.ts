import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import {
  cleanupHostProviders,
  getHostProviders,
  refreshHostProviders,
} from '@store/adcm/hostProviders/hostProvidersSlice';
import { loadRelatedData, cleanupRelatedData } from '@store/adcm/hostProviders/hostProvidersTableSlice';
import { defaultDebounceDelay } from '@constants';
import { useEffect } from 'react';

export const useRequestHostProviders = () => {
  const dispatch = useDispatch();
  const filter = useStore(({ adcm }) => adcm.hostProvidersTable.filter);
  const paginationParams = useStore(({ adcm }) => adcm.hostProvidersTable.paginationParams);
  const sortParams = useStore(({ adcm }) => adcm.hostProvidersTable.sortParams);
  const requestFrequency = useStore(({ adcm }) => adcm.hostProvidersTable.requestFrequency);

  useEffect(() => {
    dispatch(loadRelatedData());

    return () => {
      dispatch(cleanupHostProviders());
      dispatch(cleanupRelatedData());
    };
  }, [dispatch]);

  const debounceGetBundles = useDebounce(() => {
    dispatch(getHostProviders());
  }, defaultDebounceDelay);

  const debounceRefreshBundles = useDebounce(() => {
    dispatch(refreshHostProviders());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetBundles, debounceRefreshBundles, requestFrequency, [filter, paginationParams, sortParams]);
};
