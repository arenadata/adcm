import { useDispatch, useRequestTimer, useDebounce, useStore } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { getTask } from '@store/adcm/jobs/jobsSlice';
import { useParams } from 'react-router-dom';

export const useRequestJobPage = () => {
  const dispatch = useDispatch();
  const { jobId } = useParams();
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);

  const debounceGetData = useDebounce(() => {
    if (!jobId) return;
    dispatch(getTask(+jobId));
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!jobId) return;
    dispatch(getTask(+jobId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, requestFrequency, []);
};
