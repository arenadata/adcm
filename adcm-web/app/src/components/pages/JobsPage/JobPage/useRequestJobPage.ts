import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { getTask } from '@store/adcm/jobs/jobsSlice';
import { useParams } from 'react-router-dom';

export const useRequestJobPage = () => {
  const dispatch = useDispatch();
  const { jobId } = useParams();

  const debounceGetData = useDebounce(() => {
    if (!jobId) return;
    dispatch(getTask(+jobId));
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!jobId) return;
    dispatch(getTask(+jobId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, 0, []);
};
