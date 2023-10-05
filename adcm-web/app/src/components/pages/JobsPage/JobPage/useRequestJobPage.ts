import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupJobs, getTask } from '@store/adcm/jobs/jobsSlice';
import { useParams } from 'react-router-dom';
import { useEffect } from 'react';

export const useRequestJobPage = () => {
  const dispatch = useDispatch();
  const { jobId } = useParams();

  useEffect(() => {
    return () => {
      dispatch(cleanupJobs());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    if (!jobId) return;
    dispatch(getTask(+jobId));
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!jobId) return;
    dispatch(getTask(+jobId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, 0, []);
};
