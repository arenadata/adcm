import { useDispatch, usePersistSettings, useStore } from '@hooks';
import { AdcmClustersFilter, AdcmPrototypeVersions } from '@models/adcm';
import { findBy } from '@utils/arrayUtils';
import {
  setFilter,
  setPaginationParams,
  setRequestFrequency,
  setSortParams,
} from '@store/adcm/clusters/clustersTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (
  filterFromStorage: AdcmClustersFilter,
  actualFilter: AdcmClustersFilter,
  prototypes: AdcmPrototypeVersions[],
): AdcmClustersFilter => {
  const result: AdcmClustersFilter = {
    ...actualFilter,
    ...filterFromStorage,
    name: filterFromStorage.name || undefined,
    status: filterFromStorage.status || undefined,
    prototypeName: findBy(prototypes, 'name', filterFromStorage.prototypeName)
      ? filterFromStorage.prototypeName
      : undefined,
  };

  return result;
};

export const usePersistClustersTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.clustersTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.clustersTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.clustersTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.clustersTable.requestFrequency);

  const prototypes = useStore(({ adcm }) => adcm.clustersTable.relatedData.prototypes);
  const isAllDataLoaded = useStore(({ adcm }) => adcm.clustersTable.isAllDataLoaded);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/clustersTable',
      settings: {
        filter,
        sortParams,
        requestFrequency,
        perPage,
      },
      isReadyToLoad: isAllDataLoaded,
      onSettingsLoaded: (settings) => {
        const mergedFilter = mergeFilters(settings.filter, filter, prototypes);
        dispatch(setFilter(mergedFilter));
        dispatch(setSortParams(settings.sortParams));
        dispatch(setRequestFrequency(settings.requestFrequency));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [filter, sortParams, requestFrequency, perPage],
  );
};
