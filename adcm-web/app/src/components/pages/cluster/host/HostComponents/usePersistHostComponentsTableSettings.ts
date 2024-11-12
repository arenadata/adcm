import { useDispatch, usePersistSettings, useStore } from '@hooks';
import type { AdcmHostComponentsFilter } from '@models/adcm';
import { setSortParams, setFilter, setPaginationParams } from '@store/adcm/hostComponents/hostComponentsTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (
  filterFromStorage: AdcmHostComponentsFilter,
  actualFilter: AdcmHostComponentsFilter,
): AdcmHostComponentsFilter => {
  const result: AdcmHostComponentsFilter = {
    ...actualFilter,
    ...filterFromStorage,
    displayName: filterFromStorage.displayName || undefined,
  };

  return result;
};

export const usePersistHostComponentsTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.hostComponentsTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.hostComponentsTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.hostComponentsTable.paginationParams);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/hostComponentsTable',
      settings: {
        filter,
        sortParams,
        perPage,
      },
      isReadyToLoad: true,
      onSettingsLoaded: (settings) => {
        const mergedFilter = mergeFilters(settings.filter, filter);
        dispatch(setFilter(mergedFilter));
        dispatch(setSortParams(settings.sortParams));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [filter, sortParams, perPage],
  );
};
