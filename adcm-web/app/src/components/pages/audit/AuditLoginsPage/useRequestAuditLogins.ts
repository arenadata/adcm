import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { cleanupAuditLogins, getAuditLogins, refreshAuditLogins } from '@store/adcm/audit/auditLogins/auditLoginsSlice';
import { cleanupList } from '@store/adcm/audit/auditLogins/auditLoginsTableSlice';
import { defaultDebounceDelay } from '@constants';
import { useEffect } from 'react';
import { usePersistAuditLoginsTableSettings } from './usePersistAuditLoginsTableSettings';

export const useRequestAuditLogins = () => {
  const dispatch = useDispatch();
  const filter = useStore(({ adcm }) => adcm.auditLoginsTable.filter);
  const paginationParams = useStore(({ adcm }) => adcm.auditLoginsTable.paginationParams);
  const sortParams = useStore(({ adcm }) => adcm.auditLoginsTable.sortParams);
  const requestFrequency = useStore(({ adcm }) => adcm.auditLoginsTable.requestFrequency);

  usePersistAuditLoginsTableSettings();

  useEffect(() => {
    return () => {
      dispatch(cleanupAuditLogins());
      dispatch(cleanupList());
    };
  }, [dispatch]);

  const debounceGetBundles = useDebounce(() => {
    dispatch(getAuditLogins());
  }, defaultDebounceDelay);

  const debounceRefreshBundles = useDebounce(() => {
    dispatch(refreshAuditLogins());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetBundles, debounceRefreshBundles, requestFrequency, [filter, paginationParams, sortParams]);
};
