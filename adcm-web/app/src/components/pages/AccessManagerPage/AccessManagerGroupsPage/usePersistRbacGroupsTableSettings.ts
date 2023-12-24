import { useDispatch, usePersistSettings, useStore } from '@hooks';
import { AdcmGroupFilter } from '@models/adcm';
import {
  setFilter,
  setPaginationParams,
  setRequestFrequency,
  setSortParams,
} from '@store/adcm/groups/groupsTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (filterFromStorage: AdcmGroupFilter, actualFilter: AdcmGroupFilter): AdcmGroupFilter => {
  const result: AdcmGroupFilter = {
    ...actualFilter,
    ...filterFromStorage,
    displayName: filterFromStorage.displayName || undefined,
    type: filterFromStorage.type || undefined,
  };

  return result;
};

export const usePersistRbacGroupsTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.groupsTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.groupsTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.groupsTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.groupsTable.requestFrequency);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/groupsTable',
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
