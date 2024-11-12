import { useDispatch, usePersistSettings, useStore } from '@hooks';
import type { AdcmUsersFilter } from '@models/adcm';
import { setFilter, setPaginationParams, setRequestFrequency, setSortParams } from '@store/adcm/users/usersTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (filterFromStorage: AdcmUsersFilter, actualFilter: AdcmUsersFilter): AdcmUsersFilter => {
  const result: AdcmUsersFilter = {
    ...actualFilter,
    ...filterFromStorage,
    username: filterFromStorage.username || undefined,
    status: filterFromStorage.status || undefined,
    type: filterFromStorage.type || undefined,
  };

  return result;
};

export const usePersistRbacUsersTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.usersTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.usersTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.usersTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.usersTable.requestFrequency);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/usersTable',
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
