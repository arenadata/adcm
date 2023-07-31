import { useEffect } from 'react';
import { useStore, useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { getBundles, refreshBundles, cleanupBundles } from '@store/adcm/bundles/bundlesSlice';
import { loadRelatedData, cleanupRelatedData } from '@store/adcm/bundles/bundlesTableSlice';
import { defaultDebounceDelay } from '@constants';

export const useRequestBundles = () => {
  const dispatch = useDispatch();
  const filter = useStore(({ adcm }) => adcm.bundlesTable.filter);
  const paginationParams = useStore(({ adcm }) => adcm.bundlesTable.paginationParams);
  const requestFrequency = useStore(({ adcm }) => adcm.bundlesTable.requestFrequency);
  const sortParams = useStore(({ adcm }) => adcm.bundlesTable.sortParams);

  useEffect(() => {
    dispatch(loadRelatedData());

    return () => {
      dispatch(cleanupBundles());
      dispatch(cleanupRelatedData());
    };
  }, [dispatch]);

  const debounceGetBundles = useDebounce(() => {
    dispatch(getBundles());
  }, defaultDebounceDelay);

  const debounceRefreshBundles = useDebounce(() => {
    dispatch(refreshBundles());
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetBundles, debounceRefreshBundles, requestFrequency, [filter, sortParams, paginationParams]);
};
