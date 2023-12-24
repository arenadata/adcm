import { useRef, useEffect } from 'react';

export function useDidUpdate(callback: () => void, conditions?: unknown[]): void {
  const didMountRef = useRef(false);

  useEffect(() => {
    if (didMountRef.current) {
      callback();
    }
    didMountRef.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, conditions);

  // check pure unmount (dependency array is empty)
  useEffect(
    () => () => {
      didMountRef.current = false;
    },
    [],
  );
}
