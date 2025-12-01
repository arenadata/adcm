import { useLayoutEffect, useRef } from 'react';

export const useResizeElementObserver = (
  element: HTMLElement | null,
  onResize?: (width: number, height: number) => void,
  onResizeComplete?: (width: number, height: number) => void,
) => {
  const timerRef = useRef<number>();

  useLayoutEffect(() => {
    if (!element) {
      return;
    }

    const handleResize = (entries: ResizeObserverEntry[]) => {
      if (!Array.isArray(entries)) {
        return;
      }

      onResize?.(element?.offsetWidth ?? 0, element?.offsetHeight ?? 0);
      window.clearTimeout(timerRef.current);

      timerRef.current = window.setTimeout(() => {
        onResizeComplete?.(element?.offsetWidth ?? 0, element?.offsetHeight ?? 0);
      }, 600);
    };

    let observer: ResizeObserver | null = new ResizeObserver(handleResize);
    observer.observe(element);

    return () => {
      if (observer) {
        observer.disconnect();
        observer = null;
        window.clearInterval(timerRef.current);
      }
    };
  }, [element, onResize]);
};
