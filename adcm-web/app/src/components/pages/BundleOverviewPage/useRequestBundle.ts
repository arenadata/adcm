import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { cleanupBundle, getRelatedPrototype, loadBundle } from '@store/adcm/bundle/bundleSlice';

export const useRequestBundle = () => {
  const dispatch = useDispatch();
  const { bundleId: bundleIdFromUrl } = useParams();
  const bundleId = Number(bundleIdFromUrl);

  useEffect(() => {
    return () => {
      dispatch(cleanupBundle());
      dispatch(cleanupBreadcrumbs());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    if (bundleId) {
      dispatch(loadBundle(bundleId));
      dispatch(getRelatedPrototype(bundleId));
    }
  }, defaultDebounceDelay);

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  useRequestTimer(debounceGetData, () => {}, 0, [bundleId]);
};
