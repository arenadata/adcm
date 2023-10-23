import { useDispatch, usePersistSettings, useStore } from '@hooks';
import { AdcmRolesFilter } from '@models/adcm';
import { setFilter, setPaginationParams, setRequestFrequency, setSortParams } from '@store/adcm/roles/rolesTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (filterFromStorage: AdcmRolesFilter, actualFilter: AdcmRolesFilter): AdcmRolesFilter => {
  const result: AdcmRolesFilter = {
    ...actualFilter,
    ...filterFromStorage,
    displayName: filterFromStorage.displayName || undefined,
  };

  return result;
};

export const usePersistRbacRolesTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.rolesTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.rolesTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.rolesTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.rolesTable.requestFrequency);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/rolesTable',
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
