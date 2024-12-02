import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { getSubJob, refreshSubJob, cleanupSubJob } from '@store/adcm/jobs/subJobSlice';
import { AdcmJobStatus } from '@models/adcm';

export const useRequestSubJob = () => {
  const dispatch = useDispatch();
  const { subJobId } = useParams();
  const subJob = useStore(({ adcm }) => adcm.subJob.subJob);
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);

  useEffect(() => {
    return () => {
      dispatch(cleanupSubJob());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    if (subJobId) {
      dispatch(getSubJob(+subJobId));
    }
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (subJobId) {
      dispatch(refreshSubJob(+subJobId));
    }
  }, defaultDebounceDelay);

  useRequestTimer(
    debounceGetData,
    debounceRefreshData,
    subJob?.status === AdcmJobStatus.Running ? requestFrequency : 0,
    [subJobId],
  );
};
