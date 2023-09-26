import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import {
  cleanupHostProviders,
  getHostProviders,
  refreshHostProviders,
} from '@store/adcm/hostProviders/hostProvidersSlice';
import { loadRelatedData, cleanupRelatedData } from '@store/adcm/hostProviders/hostProvidersTableSlice';
import { defaultDebounceDelay } from '@constants';
import { useEffect } from 'react';
import {
  cleanupHostProviderDynamicActions,
  loadHostProvidersDynamicActions,
} from '@store/adcm/hostProviders/hostProvidersDynamicActionsSlice';

export const useRequestHostProviders = () => {
  const dispatch = useDispatch();
  const filter = useStore(({ adcm }) => adcm.hostProvidersTable.filter);
  const paginationParams = useStore(({ adcm }) => adcm.hostProvidersTable.paginationParams);
  const sortParams = useStore(({ adcm }) => adcm.hostProvidersTable.sortParams);
  const requestFrequency = useStore(({ adcm }) => adcm.hostProvidersTable.requestFrequency);
  const hostProviders = useStore(({ adcm }) => adcm.hostProviders.hostProviders);

  useEffect(() => {
    dispatch(loadRelatedData());

    return () => {
      dispatch(cleanupHostProviders());
      dispatch(cleanupRelatedData());
    };
  }, [dispatch]);

  useEffect(() => {
    if (hostProviders.length) {
      dispatch(loadHostProvidersDynamicActions(hostProviders));
    }

    return () => {
      dispatch(cleanupHostProviderDynamicActions());
    };
  }, [dispatch, hostProviders]);

  const debounceGetBundles = useDebounce(() => {
    dispatch(getHostProviders());
  }, defaultDebounceDelay);

  const debounceRefreshBundles = useDebounce(() => {
    dispatch(refreshHostProviders());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetBundles, debounceRefreshBundles, requestFrequency, [filter, paginationParams, sortParams]);
};
