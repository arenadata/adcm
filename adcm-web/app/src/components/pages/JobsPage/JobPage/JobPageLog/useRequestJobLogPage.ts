import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { getJobLog } from '@store/adcm/jobs/jobsSlice';
import { defaultDebounceDelay } from '@constants';

export const useRequestJobLogPage = (id: number | undefined) => {
  const dispatch = useDispatch();
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);

  const debounceGetData = useDebounce(() => {
    if (!id) return;
    dispatch(getJobLog(id));
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!id) return;
    dispatch(getJobLog(id));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, requestFrequency, []);
};
