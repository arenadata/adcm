import { GetScrollDataResponse, ScrollDataProps } from '@uikit/ScrollBar/ScrollBarTypes';
import { useCallback, useEffect, useRef, useState } from 'react';
import { defaultScrollData, getScrollData, useObserver } from '@uikit/ScrollBar/ScrollBarHelper';

export const useScrollBar = ({ orientation, contentRef, thumbRef, trackRef }: ScrollDataProps) => {
  const [scrollData, setScrollData] = useState<GetScrollDataResponse>(defaultScrollData);
  const initialMousePosition = useRef({ x: 0, y: 0 });

  const updateScrollData = useCallback(() => {
    if (!contentRef.current || !thumbRef.current || !thumbRef.current) return;
    setScrollData(getScrollData({ contentRef, trackRef, thumbRef, orientation }));
  }, [contentRef, orientation, trackRef, thumbRef]);

  const resizeObserver = useObserver(updateScrollData);

  useEffect(() => {
    const curContent = contentRef?.current;
    const curThumb = thumbRef?.current;

    curContent?.addEventListener('scroll', scrollHandler);
    curThumb?.addEventListener('pointerdown', onMouseDown);
    curContent?.classList.add('scrollBar');

    return () => {
      clearDocumentHandlers();
      curContent?.removeEventListener('scroll', scrollHandler);
      curThumb?.removeEventListener('pointerdown', onMouseDown);
    };
  }, [scrollData, contentRef.current, thumbRef.current, orientation]);

  const onMouseDown = useCallback(
    (e: PointerEvent) => {
      if (!thumbRef?.current || !trackRef?.current) return;

      const thumbPosition = thumbRef.current.getBoundingClientRect();
      const trackPosition = trackRef.current.getBoundingClientRect();

      initialMousePosition.current.x = e.clientX - (thumbPosition.left - trackPosition.left);
      initialMousePosition.current.y = e.clientY - (thumbPosition.top - trackPosition.top);

      thumbRef.current.setPointerCapture(e.pointerId);
      thumbRef.current.addEventListener('pointermove', onPointerMove);
      thumbRef.current.addEventListener('pointerup', onPointerUp);
    },
    [thumbRef?.current, trackRef?.current],
  );

  const scrollHandler = useCallback(() => {
    if (!thumbRef?.current || !contentRef?.current) return;

    thumbRef.current.style.transform = `translate${scrollData.upperCasedAxis}(${
      contentRef.current[`scroll${scrollData.scrollTo}`] / scrollData.scrollFactor
    }px)`;
  }, [scrollData, contentRef?.current, thumbRef?.current]);

  const onPointerMove = useCallback(
    (e: MouseEvent) => {
      if (!contentRef?.current || !trackRef?.current || !thumbRef?.current) return;

      contentRef.current[`scroll${scrollData.scrollTo}`] =
        (e[`client${scrollData.upperCasedAxis}`] - initialMousePosition.current[scrollData.axisName]) *
        scrollData.scrollFactor;
    },
    [scrollData, contentRef?.current, thumbRef?.current],
  );

  useEffect(() => {
    if (!contentRef?.current) return;
    resizeObserver.observe(contentRef.current);

    return () => {
      if (!contentRef?.current) return;
      resizeObserver.unobserve(contentRef.current);
    };
  }, [contentRef?.current]);

  const clearDocumentHandlers = () => {
    if (!thumbRef?.current) return;
    thumbRef.current.removeEventListener('pointermove', onPointerMove);
    thumbRef.current.removeEventListener('pointerup', onPointerUp);
  };

  const onPointerUp = () => {
    clearDocumentHandlers();
  };
};
