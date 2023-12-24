import { useDispatch, usePersistSettings, useStore } from '@hooks';
import { AdcmHostProvider, AdcmHostsFilter } from '@models/adcm';
import { findBy } from '@utils/arrayUtils';
import {
  setFilter,
  setPaginationParams,
  setRequestFrequency,
  setSortParams,
} from '@store/adcm/cluster/hosts/hostsTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (
  filterFromStorage: AdcmHostsFilter,
  actualFilter: AdcmHostsFilter,
  hostProviders: AdcmHostProvider[],
): AdcmHostsFilter => {
  const result: AdcmHostsFilter = {
    ...actualFilter,
    ...filterFromStorage,
    name: filterFromStorage.name || undefined,
    hostproviderName: findBy(hostProviders, 'name', filterFromStorage.hostproviderName)
      ? filterFromStorage.hostproviderName
      : undefined,
  };

  return result;
};

export const usePersistClusterHostsTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.clusterHostsTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.clusterHostsTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.clusterHostsTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.clusterHostsTable.requestFrequency);

  const hostProviders = useStore(({ adcm }) => adcm.clusterHostsTable.relatedData.hostProviders);
  const isAllDataLoaded = useStore(({ adcm }) => adcm.clusterHostsTable.relatedData.isHostProvidersLoaded);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/clusterHostsTable',
      settings: {
        filter,
        sortParams,
        requestFrequency,
        perPage,
      },
      isReadyToLoad: isAllDataLoaded,
      onSettingsLoaded: (settings) => {
        const mergedFilter = mergeFilters(settings.filter, filter, hostProviders);
        dispatch(setFilter(mergedFilter));
        dispatch(setSortParams(settings.sortParams));
        dispatch(setRequestFrequency(settings.requestFrequency));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [filter, sortParams, requestFrequency, perPage],
  );
};
