import { useDispatch, useRequestTimer, useDebounce, useStore } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupJobs, getTask } from '@store/adcm/jobs/jobsSlice';
import { useParams } from 'react-router-dom';
import { useEffect } from 'react';
import { AdcmJobStatus } from '@models/adcm';

export const useRequestJobPage = () => {
  const dispatch = useDispatch();
  const { jobId } = useParams();
  const task = useStore(({ adcm }) => adcm.jobs.task);
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);

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

  useRequestTimer(
    debounceGetData,
    debounceRefreshData,
    task.status === AdcmJobStatus.Running ? requestFrequency : 0,
    [],
  );
};
