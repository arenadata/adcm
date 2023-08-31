import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupRoles, getRoles, getProducts, refreshRoles } from '@store/adcm/roles/rolesSlice';

export const useRequestAccessManagerRoles = () => {
  const dispatch = useDispatch();
  const { filter, sortParams, paginationParams } = useStore((s) => s.adcm.rolesTable);

  useEffect(() => {
    return () => {
      dispatch(cleanupRoles());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    dispatch(getRoles());
    dispatch(getProducts());
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    dispatch(refreshRoles());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, 0, [filter, sortParams, paginationParams]);
};
