import type { PropsWithChildren } from 'react';
import type { ScrollPosition } from '@uikit/ScrollBar/ScrollBarTypes';
import s from './Scrollbar.module.scss';
import cn from 'classnames';

interface ScrollBarWrapper extends PropsWithChildren {
  position: ScrollPosition;
  className?: string;
}

const ScrollBarWrapper = ({ children, position, className }: ScrollBarWrapper) => {
  return <div className={cn(s.scrollBarWrapper, s[`scrollBarWrapper_${position}`], className)}>{children}</div>;
};

export default ScrollBarWrapper;
