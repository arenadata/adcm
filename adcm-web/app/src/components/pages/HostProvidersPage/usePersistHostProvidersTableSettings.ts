import { useDispatch, usePersistSettings, useStore } from '@hooks';
import { AdcmHostProviderFilter, AdcmPrototypeVersions } from '@models/adcm';
import { findBy } from '@utils/arrayUtils';
import {
  setFilter,
  setPaginationParams,
  setRequestFrequency,
  setSortParams,
} from '@store/adcm/hostProviders/hostProvidersTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (
  filterFromStorage: AdcmHostProviderFilter,
  actualFilter: AdcmHostProviderFilter,
  prototypes: AdcmPrototypeVersions[],
): AdcmHostProviderFilter => {
  const result: AdcmHostProviderFilter = {
    ...actualFilter,
    ...filterFromStorage,
    name: filterFromStorage.name || undefined,
    prototypeDisplayName: findBy(prototypes, 'displayName', filterFromStorage.prototypeDisplayName)
      ? filterFromStorage.prototypeDisplayName
      : undefined,
  };

  return result;
};

export const usePersistHostProvidersTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.hostProvidersTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.hostProvidersTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.hostProvidersTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.hostProvidersTable.requestFrequency);

  const prototypes = useStore(({ adcm }) => adcm.hostProvidersTable.relatedData.prototypes);
  const isAllDataLoaded = useStore(({ adcm }) => adcm.hostProvidersTable.isAllDataLoaded);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/hostProvidersTable',
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
