import { useDispatch, usePersistSettings, useStore } from '@hooks';
import { AdcmPoliciesFilter } from '@models/adcm';
import {
  setFilter,
  setPaginationParams,
  setRequestFrequency,
  setSortParams,
} from '@store/adcm/policies/policiesTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (filterFromStorage: AdcmPoliciesFilter, actualFilter: AdcmPoliciesFilter): AdcmPoliciesFilter => {
  const result: AdcmPoliciesFilter = {
    ...actualFilter,
    ...filterFromStorage,
    name: filterFromStorage.name || undefined,
  };

  return result;
};

export const usePersistRbacPoliciesTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.policiesTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.policiesTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.policiesTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.policiesTable.requestFrequency);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/policiesTable',
      settings: {
        filter,
        sortParams,
        requestFrequency,
        perPage,
      },
      isReadyToLoad: true,
      onSettingsLoaded: (settings) => {
        const mergedFilter = mergeFilters(settings.filter, filter);
        dispatch(setFilter(mergedFilter));
        dispatch(setSortParams(settings.sortParams));
        dispatch(setRequestFrequency(settings.requestFrequency));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [filter, sortParams, requestFrequency, perPage],
  );
};
