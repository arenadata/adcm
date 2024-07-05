import React, { useRef } from 'react';
import { ScrollBarProps } from '@uikit/ScrollBar/ScrollBarTypes';
import { useScrollBar } from '@uikit/ScrollBar/useScrollBar';
import s from '@uikit/ScrollBar/Scrollbar.module.scss';
import cn from 'classnames';

const ScrollBar = ({ contentRef, orientation, trackClasses, thumbClasses, thumbCaptureRadius = 6 }: ScrollBarProps) => {
  const thumbRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  useScrollBar({ contentRef, thumbRef, trackRef, orientation });

  const trackClassName = cn(s.defaultTrack, s[`defaultTrack_${orientation}`], trackClasses);
  const thumbClassName = cn(s.defaultThumb, thumbClasses);
  const thumbStyles = {
    height: '100%',
    '--thumb-capture-radius': `${thumbCaptureRadius}px`,
  };

  return (
    <div
      ref={trackRef}
      className={trackClassName}
      draggable={false}
      style={thumbStyles}
      data-scroll={`scroll-track-${orientation}`}
    >
      <div ref={thumbRef} className={thumbClassName} draggable={false} />
    </div>
  );
};

export default ScrollBar;
