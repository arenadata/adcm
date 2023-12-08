import { useDispatch, usePersistSettings, useStore } from '@hooks';
import {
  setPaginationParams,
  setSortParams,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

export const usePersistServiceComponentsTableSettings = () => {
  const dispatch = useDispatch();

  const sortParams = useStore(({ adcm }) => adcm.serviceComponentsTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.serviceComponentsTable.paginationParams);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/serviceComponentsTable',
      settings: {
        sortParams,
        perPage,
      },
      isReadyToLoad: true,
      onSettingsLoaded: (settings) => {
        dispatch(setSortParams(settings.sortParams));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [sortParams, perPage],
  );
};
