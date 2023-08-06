import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupUsers, getUsers, refreshUsers } from '@store/adcm/users/usersSlice';

export const useRequestAccessManagerUsers = () => {
  const dispatch = useDispatch();
  const filter = useStore((s) => s.adcm.usersTable.filter);
  const sortParams = useStore((s) => s.adcm.usersTable.sortParams);
  const paginationParams = useStore((s) => s.adcm.usersTable.paginationParams);

  useEffect(() => {
    return () => {
      dispatch(cleanupUsers());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    dispatch(getUsers());
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    dispatch(refreshUsers());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, 0, [filter, sortParams, paginationParams]);
};
