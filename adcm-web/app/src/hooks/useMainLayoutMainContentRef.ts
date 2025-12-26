import { useRef, useEffect } from 'react';

export const useMainLayoutMainContentRef = () => {
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const wrapper = document.getElementById('mainLayout__mainContent');
    if (wrapper instanceof HTMLDivElement) {
      wrapperRef.current = wrapper;
    }
  }, []);

  return { wrapperRef };
};
