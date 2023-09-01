import { useEffect } from 'react';
import { useDispatch } from '@hooks';
import { getJobLog } from '@store/adcm/jobs/jobsSlice';

export const useRequestJobLogPage = (id: number | undefined) => {
  const dispatch = useDispatch();

  useEffect(() => {
    return () => {
      if (!id) return;
      dispatch(getJobLog(id));
    };
  }, [id, dispatch]);
};
