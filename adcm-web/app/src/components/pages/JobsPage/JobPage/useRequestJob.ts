import { useDispatch, useRequestTimer, useDebounce, useStore } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupJob, getJob, refreshJob } from '@store/adcm/jobs/jobSlice';
import { useParams } from 'react-router-dom';
import { useEffect } from 'react';
import { AdcmJobStatus } from '@models/adcm';

export const useRequestJob = () => {
  const dispatch = useDispatch();
  const params = useParams();
  const jobId = params.jobId;
  const job = useStore(({ adcm }) => adcm.job.job);
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);

  useEffect(() => {
    return () => {
      dispatch(cleanupJob());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    if (!jobId) return;
    dispatch(getJob(+jobId));
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!jobId) return;
    dispatch(refreshJob(+jobId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, job?.status === AdcmJobStatus.Running ? requestFrequency : 0, [
    jobId,
  ]);
};
