import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { cleanupAuditLogins, getAuditLogins, refreshAuditLogins } from '@store/adcm/audit/auditLogins/auditLoginsSlice';
import { defaultDebounceDelay } from '@constants';
import { useEffect } from 'react';

export const useRequestAuditLogins = () => {
  const dispatch = useDispatch();
  const filter = useStore(({ adcm }) => adcm.auditLoginsTable.filter);
  const paginationParams = useStore(({ adcm }) => adcm.auditLoginsTable.paginationParams);
  const sortParams = useStore(({ adcm }) => adcm.auditLoginsTable.sortParams);
  const requestFrequency = useStore(({ adcm }) => adcm.auditLoginsTable.requestFrequency);

  useEffect(() => {
    return () => {
      dispatch(cleanupAuditLogins());
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
