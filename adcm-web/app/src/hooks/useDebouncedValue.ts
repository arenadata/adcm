import { useEffect, useState } from 'react';
import { defaultDebounceDelay } from '@constants';

export const useDebouncedValue = <T>(value: T, delay: number = defaultDebounceDelay): T => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    if (delay <= 0) {
      setDebouncedValue(value);
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [value, delay]);

  return delay <= 0 ? value : debouncedValue;
};
