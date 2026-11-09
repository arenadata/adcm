import { useEffect, useRef } from 'react';
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
  const parentTaskStatus = subJob?.parentTask.status;
  const prevParentStatusRef = useRef(parentTaskStatus);

  useEffect(() => {
    return () => {
      dispatch(cleanupSubJob());
    };
  }, [dispatch]);

  // WS update_task updates parent task status only, refetch subjob to sync its own status.
  useEffect(() => {
    const prevStatus = prevParentStatusRef.current;
    prevParentStatusRef.current = parentTaskStatus;

    if (!subJobId || !parentTaskStatus || prevStatus == null || prevStatus === parentTaskStatus) {
      return;
    }

    dispatch(refreshSubJob(+subJobId));
  }, [parentTaskStatus, subJobId, dispatch]);

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

  const isSubJobInProgress =
    subJob?.status === AdcmJobStatus.Running ||
    subJob?.status === AdcmJobStatus.Terminating ||
    subJob?.status === AdcmJobStatus.Revoking;

  useRequestTimer(debounceGetData, debounceRefreshData, isSubJobInProgress ? requestFrequency : 0, [subJobId]);
};
