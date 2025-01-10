import type { MutableRefObject } from 'react';
import { useEffect } from 'react';

type OutsideClickRefType = MutableRefObject<HTMLElement | null>;
type OutsideClickCallbackType = (el: EventTarget | null) => void;

export const useOutsideClick = (ref: OutsideClickRefType, callback: OutsideClickCallbackType) => {
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as HTMLElement)) {
        callback(event.target);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [ref, callback]);
};
