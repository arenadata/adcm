import { useEffect } from 'react';

export const useMediaQuery = (mediaQuery: string, onChange: (isMatch: boolean) => void) => {
  useEffect(() => {
    const mql = window.matchMedia(mediaQuery);

    const handleMql = (event: MediaQueryListEvent) => {
      onChange(event.matches);
    };

    mql.addEventListener('change', handleMql);

    // call first time
    onChange(mql.matches);

    return () => {
      mql.removeEventListener('change', handleMql);
    };
  }, [mediaQuery, onChange]);
};
