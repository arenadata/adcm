import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupGroups, getGroups, refreshGroups } from '@store/adcm/groups/groupsSlice';

export const useRequestAccessManagerGroups = () => {
  const dispatch = useDispatch();
  const { filter, sortParams, paginationParams } = useStore((s) => s.adcm.groupsTable);

  useEffect(() => {
    return () => {
      dispatch(cleanupGroups());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    dispatch(getGroups());
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    dispatch(refreshGroups());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, 0, [filter, sortParams, paginationParams]);
};
