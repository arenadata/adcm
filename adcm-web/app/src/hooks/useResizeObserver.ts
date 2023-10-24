import { useLayoutEffect, useCallback, RefObject } from 'react';

export const useResizeObserver = (ref: RefObject<HTMLElement>, callback?: () => void) => {
  const handleResize = useCallback(
    (entries: ResizeObserverEntry[]) => {
      if (!Array.isArray(entries)) {
        return;
      }

      callback?.();
    },
    [callback],
  );

  useLayoutEffect(() => {
    if (!ref.current) {
      return;
    }

    let observer: ResizeObserver | null = new ResizeObserver((entries: ResizeObserverEntry[]) => handleResize(entries));
    observer.observe(ref.current);

    return () => {
      if (observer) {
        observer.disconnect();
        observer = null;
      }
    };
  }, [ref, handleResize]);
};
