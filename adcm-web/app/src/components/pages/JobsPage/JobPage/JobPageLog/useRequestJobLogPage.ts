import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { getJobLog } from '@store/adcm/jobs/jobsSlice';
import { defaultDebounceDelay } from '@constants';
import { AdcmJobStatus } from '@models/adcm';
import { useMemo, useState } from 'react';

const maxFuseRequestCount = 2;

export const useRequestJobLogPage = (id: number | undefined) => {
  const dispatch = useDispatch();
  const task = useStore(({ adcm }) => adcm.jobs.task);
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);
  const [fuseRequestCount, setFuseRequestCount] = useState(0);

  const debounceGetData = useDebounce(() => {
    if (!id) return;
    dispatch(getJobLog(id));
  }, defaultDebounceDelay);

  const isNeedUpdate = useMemo(() => {
    if (!task.childJobs || fuseRequestCount >= maxFuseRequestCount) return false;

    const curJob = task.childJobs.find((job) => job.id == id);

    if (!curJob) return false;

    if (curJob.status === AdcmJobStatus.Created) return true;

    if (curJob.status !== AdcmJobStatus.Running && task.status !== AdcmJobStatus.Running) {
      setFuseRequestCount((prevState) => prevState + 1);
    }

    return true;
  }, [task, fuseRequestCount, id]);

  useRequestTimer(debounceGetData, debounceGetData, isNeedUpdate ? requestFrequency : 0, [id]);
};
