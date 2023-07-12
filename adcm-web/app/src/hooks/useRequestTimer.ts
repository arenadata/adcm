import { useEffect, useRef, useCallback } from 'react';

export const useRequestTimer = (
  initialRequest: () => void,
  refreshRequest: () => void,
  requestFrequency: number, // in seconds
  depsArray: unknown[] = [],
) => {
  const timerRef = useRef<number | null>(null);

  const initTimer = useCallback(
    (isInitialRequestRequired: boolean) => {
      timerRef.current && clearInterval(timerRef.current);
      isInitialRequestRequired && initialRequest();

      if (requestFrequency) {
        timerRef.current = window.setInterval(() => {
          refreshRequest();
        }, requestFrequency * 1000);
      }
    },
    [initialRequest, refreshRequest, requestFrequency],
  );

  useEffect(() => {
    initTimer(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, depsArray);

  useEffect(() => {
    initTimer(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestFrequency]);

  useEffect(
    () => () => {
      timerRef.current && window.clearInterval(timerRef.current);
      timerRef.current = null;
    },
    [],
  );
};
