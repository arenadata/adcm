import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { getJobLog } from '@store/adcm/jobs/jobsSlice';
import { defaultDebounceDelay } from '@constants';
import { AdcmJobStatus } from '@models/adcm';
import { useMemo, useState } from 'react';

export const useRequestJobLogPage = (id: number | undefined) => {
  const dispatch = useDispatch();
  const task = useStore(({ adcm }) => adcm.jobs.task);
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);
  const [isLastUpdated, setIsLastUpdated] = useState(false);

  const debounceGetData = useDebounce(() => {
    if (!id) return;
    dispatch(getJobLog(id));
  }, defaultDebounceDelay);

  const isNeedUpdate = useMemo(() => {
    if (!task.childJobs || isLastUpdated) return false;

    const curJob = task.childJobs.find((job) => job.id == id);

    if (!curJob) return false;
    if (curJob.status === AdcmJobStatus.Created) return true;

    if (curJob.status !== AdcmJobStatus.Running && task.status !== AdcmJobStatus.Running) {
      setIsLastUpdated(true);
      return true;
    }

    return true;
  }, [task, isLastUpdated, id]);

  useRequestTimer(debounceGetData, debounceGetData, isNeedUpdate ? requestFrequency : 0, [id]);
};
