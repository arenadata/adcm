import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import {
  cleanupAuditOperations,
  getAuditOperations,
  refreshAuditOperations,
} from '@store/adcm/audit/auditOperations/auditOperationsSlice';
import { cleanupList } from '@store/adcm/audit/auditOperations/auditOperationsTableSlice';
import { defaultDebounceDelay } from '@constants';
import { useEffect } from 'react';
import { usePersistAuditOperationsTableSettings } from './usePersistAuditOperationsTableSettings';

export const useRequestAuditOperations = () => {
  const dispatch = useDispatch();
  const filter = useStore(({ adcm }) => adcm.auditOperationsTable.filter);
  const paginationParams = useStore(({ adcm }) => adcm.auditOperationsTable.paginationParams);
  const sortParams = useStore(({ adcm }) => adcm.auditOperationsTable.sortParams);
  const requestFrequency = useStore(({ adcm }) => adcm.auditOperationsTable.requestFrequency);

  usePersistAuditOperationsTableSettings();

  useEffect(() => {
    return () => {
      dispatch(cleanupAuditOperations());
      dispatch(cleanupList());
    };
  }, [dispatch]);

  const debounceGetBundles = useDebounce(() => {
    dispatch(getAuditOperations());
  }, defaultDebounceDelay);

  const debounceRefreshBundles = useDebounce(() => {
    dispatch(refreshAuditOperations());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetBundles, debounceRefreshBundles, requestFrequency, [filter, paginationParams, sortParams]);
};
