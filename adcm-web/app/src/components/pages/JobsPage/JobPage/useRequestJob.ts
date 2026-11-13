import { useDispatch, useRequestTimer, useDebounce, useStore } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupJob, getJob, refreshJob } from '@store/adcm/jobs/jobSlice';
import { useParams } from 'react-router-dom';
import { useEffect, useRef } from 'react';
import { AdcmJobStatus } from '@models/adcm';

export const useRequestJob = () => {
  const dispatch = useDispatch();
  const params = useParams();
  const jobId = params.jobId;
  const job = useStore(({ adcm }) => adcm.job.job);
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);
  const prevStatusRef = useRef(job?.status);

  useEffect(() => {
    return () => {
      dispatch(cleanupJob());
    };
  }, [dispatch]);

  // WS update_task sends only task status, refetch when status changes to sync childJobs.
  useEffect(() => {
    const prevStatus = prevStatusRef.current;
    prevStatusRef.current = job?.status;

    if (!jobId || !job?.status || prevStatus == null || prevStatus === job.status) {
      return;
    }

    dispatch(refreshJob(+jobId));
  }, [job?.status, jobId, dispatch]);

  const debounceGetData = useDebounce(() => {
    if (!jobId) return;
    dispatch(getJob(+jobId));
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!jobId) return;
    dispatch(refreshJob(+jobId));
  }, defaultDebounceDelay);

  const isJobInProgress =
    job?.status === AdcmJobStatus.Running ||
    job?.status === AdcmJobStatus.Terminating ||
    job?.status === AdcmJobStatus.Revoking;

  useRequestTimer(debounceGetData, debounceRefreshData, isJobInProgress ? requestFrequency : 0, [jobId]);
};
