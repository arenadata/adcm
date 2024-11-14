import { useDispatch, usePersistSettings, useStore } from '@hooks';
import type { AdcmAuditLoginFilter } from '@models/adcm';
import {
  setFilter,
  setPaginationParams,
  setRequestFrequency,
  setSortParams,
} from '@store/adcm/audit/auditLogins/auditLoginsTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (
  filterFromStorage: AdcmAuditLoginFilter,
  actualFilter: AdcmAuditLoginFilter,
): AdcmAuditLoginFilter => {
  const result: AdcmAuditLoginFilter = {
    ...actualFilter,
    ...filterFromStorage,
    login: filterFromStorage.login || undefined,
    loginResult: filterFromStorage.loginResult || undefined,
  };

  return result;
};

export const usePersistAuditLoginsTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.auditLoginsTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.auditLoginsTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.auditLoginsTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.auditLoginsTable.requestFrequency);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/auditLoginsTable',
      settings: {
        filter,
        sortParams,
        requestFrequency,
        perPage,
      },
      isReadyToLoad: true,
      onSettingsLoaded: (settings) => {
        const { timeFrom, timeTo, ...mergedFilter } = mergeFilters(settings.filter, filter);
        dispatch(setFilter(mergedFilter));
        dispatch(setSortParams(settings.sortParams));
        dispatch(setRequestFrequency(settings.requestFrequency));
        dispatch(setPaginationParams(mergePaginationParams(settings.perPage, paginationParams)));
      },
    },
    [filter, sortParams, requestFrequency, perPage],
  );
};
