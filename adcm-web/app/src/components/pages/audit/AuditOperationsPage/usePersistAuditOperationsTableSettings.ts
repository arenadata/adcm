import { useDispatch, usePersistSettings, useStore } from '@hooks';
import { AdcmAuditOperationFilter } from '@models/adcm';
import {
  setFilter,
  setPaginationParams,
  setRequestFrequency,
  setSortParams,
} from '@store/adcm/audit/auditOperations/auditOperationsTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (
  filterFromStorage: AdcmAuditOperationFilter,
  actualFilter: AdcmAuditOperationFilter,
): AdcmAuditOperationFilter => {
  const result: AdcmAuditOperationFilter = {
    ...actualFilter,
    ...filterFromStorage,
    objectName: filterFromStorage.objectName || undefined,
    username: filterFromStorage.username || undefined,
    objectType: filterFromStorage.objectType || undefined,
    operationType: filterFromStorage.operationType || undefined,
    operationResult: filterFromStorage.operationResult || undefined,
    timeFrom: filterFromStorage.timeFrom || actualFilter.timeFrom,
    timeTo: filterFromStorage.timeTo || actualFilter.timeTo,
  };

  return result;
};

export const usePersistAuditOperationsTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.auditOperationsTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.auditOperationsTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.auditOperationsTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.auditOperationsTable.requestFrequency);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/auditOperationsTable',
      settings: {
        filter,
        sortParams,
        requestFrequency,
        perPage,
      },
      isReadyToLoad: true,
      onSettingsLoaded: (settings) => {
        const mergedFilter = mergeFilters(settings.filter, filter);
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { timeFrom, timeTo, ...filterForLocalStorage } = mergedFilter;

        dispatch(setFilter(filterForLocalStorage));
        dispatch(setSortParams(settings.sortParams));
        dispatch(setRequestFrequency(settings.requestFrequency));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [filter, sortParams, requestFrequency, perPage],
  );
};
