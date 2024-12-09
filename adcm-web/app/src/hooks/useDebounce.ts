import { useEffect, useRef } from 'react';

type UnknownFunction = (...args: unknown[]) => unknown;

export const useDebounce = (callback: UnknownFunction, delay: number) => {
  const timeoutRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    },
    [],
  );

  // biome-ignore lint/suspicious/noExplicitAny:
  return (...args: any[]) => {
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = window.setTimeout(() => callback(...args), delay);
  };
};
