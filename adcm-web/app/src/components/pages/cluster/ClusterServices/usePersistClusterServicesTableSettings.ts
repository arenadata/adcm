import { useDispatch, usePersistSettings, useStore } from '@hooks';
import type { AdcmServicesFilter } from '@models/adcm';
import {
  setFilter,
  setPaginationParams,
  setRequestFrequency,
  setSortParams,
} from '@store/adcm/cluster/services/servicesTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (filterFromStorage: AdcmServicesFilter, actualFilter: AdcmServicesFilter): AdcmServicesFilter => {
  const result: AdcmServicesFilter = {
    ...actualFilter,
    ...filterFromStorage,
    displayName: filterFromStorage.displayName || undefined,
  };

  return result;
};

export const usePersistClusterServicesTableSettings = () => {
  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const filter = useStore(({ adcm }) => adcm.servicesTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.servicesTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.servicesTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.servicesTable.requestFrequency);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/servicesTable',
      settings: {
        clusterId: cluster?.id,
        filter,
        sortParams,
        requestFrequency,
        perPage,
      },
      isReadyToLoad: true,
      onSettingsLoaded: (settings) => {
        if (settings.clusterId === cluster?.id) {
          const mergedFilter = mergeFilters(settings.filter, filter);
          dispatch(setFilter(mergedFilter));
        }
        dispatch(setSortParams(settings.sortParams));
        dispatch(setRequestFrequency(settings.requestFrequency));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [filter, sortParams, requestFrequency, perPage],
  );
};
