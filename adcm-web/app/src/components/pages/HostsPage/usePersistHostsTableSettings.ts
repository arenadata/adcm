import { useDispatch, usePersistSettings, useStore } from '@hooks';
import type { AdcmCluster, AdcmHostProvider, AdcmHostsFilter } from '@models/adcm';
import { findBy } from '@utils/arrayUtils';
import { setFilter, setPaginationParams, setRequestFrequency, setSortParams } from '@store/adcm/hosts/hostsTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (
  filterFromStorage: AdcmHostsFilter,
  actualFilter: AdcmHostsFilter,
  clusters: AdcmCluster[],
  hostProviders: AdcmHostProvider[],
): AdcmHostsFilter => {
  const result: AdcmHostsFilter = {
    ...actualFilter,
    ...filterFromStorage,
    name: filterFromStorage.name || undefined,
    hostproviderName: findBy(hostProviders, 'name', filterFromStorage.hostproviderName)
      ? filterFromStorage.hostproviderName
      : undefined,
    clusterName: findBy(clusters, 'name', filterFromStorage.clusterName) ? filterFromStorage.clusterName : undefined,
  };

  return result;
};

export const usePersistHostsTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.hostsTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.hostsTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.hostsTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.hostsTable.requestFrequency);

  const clusters = useStore(({ adcm }) => adcm.hostsTable.relatedData.clusters);
  const hostProviders = useStore(({ adcm }) => adcm.hostsTable.relatedData.hostProviders);
  const isAllDataLoaded = useStore(({ adcm }) => adcm.hostsTable.isAllDataLoaded);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/hostsTable',
      settings: {
        filter,
        sortParams,
        requestFrequency,
        perPage,
      },
      isReadyToLoad: isAllDataLoaded,
      onSettingsLoaded: (settings) => {
        const mergedFilter = mergeFilters(settings.filter, filter, clusters, hostProviders);
        dispatch(setFilter(mergedFilter));
        dispatch(setSortParams(settings.sortParams));
        dispatch(setRequestFrequency(settings.requestFrequency));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [filter, sortParams, requestFrequency, perPage],
  );
};
