import React from 'react';
import { PopoverWidth } from '@uikit/Popover/Popover.types';
export const getRefWidth = (ref: React.RefObject<HTMLElement>): number | undefined => {
  return ref?.current?.getBoundingClientRect().width;
};

export const getWidthStyles = (
  dependencyWidth: PopoverWidth,
  parentRef: React.RefObject<HTMLElement>,
): React.CSSProperties => {
  const parentWidth = getRefWidth(parentRef);

  if (dependencyWidth === 'min-parent') {
    return {
      minWidth: parentWidth,
    };
  }

  if (dependencyWidth === 'max-parent') {
    return {
      maxWidth: parentWidth,
    };
  }

  return {
    width: parentWidth,
  };
};
