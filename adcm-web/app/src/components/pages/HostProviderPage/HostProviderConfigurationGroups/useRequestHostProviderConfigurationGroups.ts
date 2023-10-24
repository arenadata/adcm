import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { useParams } from 'react-router-dom';
import { useEffect } from 'react';
import { defaultDebounceDelay } from '@constants';
import { cleanupList } from '@store/adcm/hostProvider/configurationGroups/hostProviderConfigGroupsTableSlice';
import {
  cleanupHostProviderConfigGroups,
  getHostProviderConfigGroups,
  refreshHostProviderConfigGroups,
} from '@store/adcm/hostProvider/configurationGroups/hostProviderConfigGroupsSlice';

export const useRequestHostProviderConfigurationGroups = () => {
  const dispatch = useDispatch();
  const { hostproviderId: hostproviderIdFromUrl } = useParams();
  const hostProviderId = Number(hostproviderIdFromUrl);
  const sortParams = useStore((s) => s.adcm.hostProviderConfigGroupsTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.hostProviderConfigGroupsTable.paginationParams);
  const requestFrequency = useStore((s) => s.adcm.hostProviderConfigGroupsTable.requestFrequency);

  useEffect(
    () => () => {
      dispatch(cleanupHostProviderConfigGroups());
      dispatch(cleanupList());
    },
    [dispatch],
  );

  const debounceGetHostProviderHosts = useDebounce(() => {
    dispatch(getHostProviderConfigGroups(hostProviderId));
  }, defaultDebounceDelay);

  const debounceRefreshHostProviderHosts = useDebounce(() => {
    dispatch(refreshHostProviderConfigGroups(hostProviderId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetHostProviderHosts, debounceRefreshHostProviderHosts, requestFrequency, [
    sortParams,
    paginationParams,
  ]);
};
