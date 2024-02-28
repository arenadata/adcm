import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { cleanupBundle, getBundle } from '@store/adcm/bundle/bundleSlice';

export const useRequestBundle = () => {
  const dispatch = useDispatch();
  const { bundleId: bundleIdFromUrl } = useParams();
  const bundleId = Number(bundleIdFromUrl);

  useEffect(() => {
    return () => {
      dispatch(cleanupBundle());
    };
  }, [dispatch]);

  const debounceGetData = useDebounce(() => {
    if (bundleId) {
      dispatch(getBundle(bundleId));
    }
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, () => {}, 0, [bundleId]);
};
