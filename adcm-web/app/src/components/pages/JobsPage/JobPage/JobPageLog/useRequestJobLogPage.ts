import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { getJobLog } from '@store/adcm/jobs/jobsSlice';
import { defaultDebounceDelay } from '@constants';
import { AdcmJobStatus } from '@models/adcm';

export const useRequestJobLogPage = (id: number | undefined) => {
  const dispatch = useDispatch();
  const task = useStore(({ adcm }) => adcm.jobs.task);
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);

  const debounceGetData = useDebounce(() => {
    if (!id) return;
    dispatch(getJobLog(id));
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!id) return;
    dispatch(getJobLog(id));
  }, defaultDebounceDelay);

  useRequestTimer(
    debounceGetData,
    debounceRefreshData,
    task.status === AdcmJobStatus.Running ? requestFrequency : 0,
    [],
  );
};
