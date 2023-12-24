import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupUsers, getUsers, refreshUsers } from '@store/adcm/users/usersSlice';
import { cleanupList } from '@store/adcm/users/usersTableSlice';
import { usePersistRbacUsersTableSettings } from './usePersistRbacUsersTableSettings';

export const useRequestAccessManagerUsers = () => {
  const dispatch = useDispatch();
  const { filter, sortParams, paginationParams } = useStore((s) => s.adcm.usersTable);

  usePersistRbacUsersTableSettings();

  useEffect(() => {
    return () => {
      dispatch(cleanupUsers());
      dispatch(cleanupList());
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
