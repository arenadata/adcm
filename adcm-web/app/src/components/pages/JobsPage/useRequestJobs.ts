import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupJobs, getJobs, refreshJobs } from '@store/adcm/jobs/jobsSlice';

export const useRequestJobs = () => {
  const dispatch = useDispatch();
  const filter = useStore((s) => s.adcm.jobsTable.filter);
  const sortParams = useStore((s) => s.adcm.jobsTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.jobsTable.paginationParams);
  const { requestFrequency } = useStore(({ adcm }) => adcm.jobsTable);

  useEffect(() => {
    return () => {
      dispatch(cleanupJobs());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    dispatch(getJobs());
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    dispatch(refreshJobs());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, requestFrequency, [filter, sortParams, paginationParams]);
};
