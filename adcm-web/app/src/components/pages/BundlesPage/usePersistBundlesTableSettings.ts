import { useDispatch, usePersistSettings, useStore } from '@hooks';
import type { AdcmPrototypeVersions } from '@models/adcm';
import { findBy } from '@utils/arrayUtils';
import {
  setFilter,
  setPaginationParams,
  setRequestFrequency,
  setSortParams,
} from '@store/adcm/bundles/bundlesTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';
import type { AdcmBundlesFilter } from '@models/adcm/bundle';
import { LoadState } from '@models/loadState';

const mergeFilters = (
  filterFromStorage: AdcmBundlesFilter,
  actualFilter: AdcmBundlesFilter,
  products: AdcmPrototypeVersions[],
): AdcmBundlesFilter => {
  const result: AdcmBundlesFilter = {
    ...actualFilter,
    ...filterFromStorage,
    displayName: filterFromStorage.displayName || undefined,
    product: findBy(products, 'name', filterFromStorage.product) ? filterFromStorage.product : undefined,
  };

  return result;
};

export const usePersistBundlesTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.bundlesTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.bundlesTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.bundlesTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.bundlesTable.requestFrequency);

  const products = useStore(({ adcm }) => adcm.bundlesTable.relatedData.products);
  const isAllDataLoaded = useStore(({ adcm }) => adcm.bundlesTable.relatedData.productsLoadState) === LoadState.Loaded;

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/bundlesTable',
      settings: {
        filter,
        sortParams,
        requestFrequency,
        perPage,
      },
      isReadyToLoad: isAllDataLoaded,
      onSettingsLoaded: (settings) => {
        const mergedFilter = mergeFilters(settings.filter, filter, products);
        dispatch(setFilter(mergedFilter));
        dispatch(setSortParams(settings.sortParams));
        dispatch(setRequestFrequency(settings.requestFrequency));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [filter, sortParams, requestFrequency, perPage],
  );
};
