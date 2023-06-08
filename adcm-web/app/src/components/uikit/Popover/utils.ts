import React from 'react';
export const getRefWidth = (ref: React.RefObject<HTMLElement>): number | undefined => {
  return ref?.current?.getBoundingClientRect().width;
};
