import type { PropsWithChildren, RefObject } from 'react';
import { useRef } from 'react';
import ScrollBar from '@uikit/ScrollBar/ScrollBar';
import ScrollBarWrapper from '@uikit/ScrollBar/ScrollBarWrapper';
import cn from 'classnames';
import s from './Scrollbar.module.scss';

interface ScrollerProps extends PropsWithChildren {
  className?: string;
  forwardRef?: RefObject<HTMLDivElement>;
}

const Scroller = ({ children, className = '', forwardRef }: ScrollerProps) => {
  const localRef = useRef(null);
  const wrapperRef = forwardRef ? forwardRef : localRef;

  return (
    <div className={cn(className, s.scrollerContainer)} ref={wrapperRef}>
      {children}
      <ScrollBarWrapper position="right">
        <ScrollBar orientation="vertical" contentRef={wrapperRef} />
      </ScrollBarWrapper>
      <ScrollBarWrapper position="bottom">
        <ScrollBar orientation="horizontal" contentRef={wrapperRef} />
      </ScrollBarWrapper>
    </div>
  );
};

export default Scroller;
