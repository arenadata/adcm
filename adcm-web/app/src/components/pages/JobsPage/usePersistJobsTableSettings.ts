import { useDispatch, usePersistSettings, useStore } from '@hooks';
import { AdcmJobsFilter } from '@models/adcm';
import { setFilter, setPaginationParams, setRequestFrequency, setSortParams } from '@store/adcm/jobs/jobsTableSlice';
import { mergePaginationParams } from '@hooks/usePersistSettings';

const mergeFilters = (filterFromStorage: AdcmJobsFilter, actualFilter: AdcmJobsFilter): AdcmJobsFilter => {
  const result: AdcmJobsFilter = {
    ...actualFilter,
    ...filterFromStorage,
    jobName: filterFromStorage.jobName || undefined,
    status: filterFromStorage.status || undefined,
    objectName: filterFromStorage.objectName || undefined,
  };

  return result;
};

export const usePersistJobsTableSettings = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.jobsTable.filter);
  const sortParams = useStore(({ adcm }) => adcm.jobsTable.sortParams);
  const paginationParams = useStore(({ adcm }) => adcm.jobsTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);

  const { perPage } = paginationParams;

  usePersistSettings(
    {
      localStorageKey: 'adcm/jobsTable',
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
