import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupPolicies, getPolicies, refreshPolicies } from '@store/adcm/policies/policiesSlice';
import { cleanupList } from '@store/adcm/policies/policiesTableSlice';
import { usePersistRbacPoliciesTableSettings } from './usePersistRbacPoliciesTableSettings';

export const useRequestAccessManagerPolicies = () => {
  const dispatch = useDispatch();
  const { filter, sortParams, paginationParams } = useStore((s) => s.adcm.policiesTable);

  usePersistRbacPoliciesTableSettings();

  useEffect(() => {
    return () => {
      dispatch(cleanupPolicies());
      dispatch(cleanupList());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    dispatch(getPolicies());
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    dispatch(refreshPolicies());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, 0, [filter, sortParams, paginationParams]);
};
