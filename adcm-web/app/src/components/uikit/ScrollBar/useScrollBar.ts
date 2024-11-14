import type { GetScrollDataResponse, ScrollDataProps } from '@uikit/ScrollBar/ScrollBarTypes';
import { useCallback, useEffect, useRef, useState } from 'react';
import { defaultScrollData, getScrollData, useObserver } from '@uikit/ScrollBar/ScrollBarHelper';

export const useScrollBar = ({ orientation, contentRef, thumbRef, trackRef }: ScrollDataProps) => {
  const [scrollData, setScrollData] = useState<GetScrollDataResponse>(defaultScrollData);
  const initialMousePosition = useRef({ x: 0, y: 0 });
  const [contentWrapper, setContentWrapper] = useState<Element | null>(null);

  // Problem place. Here used useEffect with useState instead of useMemo because with some reason
  // contentWrapper = useMemo( () => contentRef?.current?.children[0] || null, [contentRef]); doesn't update, so
  // contentWrapper always equal null, but useEffect + useState works well.
  useEffect(() => {
    setContentWrapper(contentRef?.current?.children[0] || null);
  }, [contentRef]);

  const updateScrollData = useCallback(() => {
    if (!contentRef.current || !thumbRef.current || !trackRef.current) return;
    setScrollData(getScrollData({ contentRef, trackRef, thumbRef, orientation }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentRef?.current, orientation, trackRef, thumbRef]);

  const resizeObserver = useObserver(updateScrollData);

  const scrollHandler = useCallback(() => {
    if (!thumbRef?.current || !contentRef?.current) return;
    thumbRef.current.style.transform = `translate${scrollData.upperCasedAxis}(${
      contentRef.current[`scroll${scrollData.scrollTo}`] / scrollData.scrollFactor
    }px)`;
  }, [scrollData, contentRef, thumbRef]);

  const onPointerMove = useCallback(
    (e: MouseEvent) => {
      if (!contentRef?.current || !trackRef?.current || !thumbRef?.current) return;

      contentRef.current[`scroll${scrollData.scrollTo}`] =
        (e[`client${scrollData.upperCasedAxis}`] - initialMousePosition.current[scrollData.axisName]) *
        scrollData.scrollFactor;
    },
    [scrollData, contentRef, thumbRef, trackRef],
  );

  const clearDocumentHandlers = useCallback(() => {
    if (!thumbRef?.current) return;
    thumbRef.current.removeEventListener('pointermove', onPointerMove);
    thumbRef.current.removeEventListener('pointerup', clearDocumentHandlers);
  }, [thumbRef, onPointerMove]);

  const onMouseDown = useCallback(
    (e: PointerEvent) => {
      if (!thumbRef?.current || !trackRef?.current) return;

      const thumbPosition = thumbRef.current.getBoundingClientRect();
      const trackPosition = trackRef.current.getBoundingClientRect();

      initialMousePosition.current.x = e.clientX - (thumbPosition.left - trackPosition.left);
      initialMousePosition.current.y = e.clientY - (thumbPosition.top - trackPosition.top);

      thumbRef.current.setPointerCapture(e.pointerId);
      thumbRef.current.addEventListener('pointermove', onPointerMove);
      thumbRef.current.addEventListener('pointerup', clearDocumentHandlers);
    },
    [thumbRef, trackRef, onPointerMove, clearDocumentHandlers],
  );

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
  }, [contentRef, thumbRef, clearDocumentHandlers, scrollHandler, onMouseDown]);

  useEffect(() => {
    if (contentWrapper === null) return;
    const content = contentWrapper;
    resizeObserver.observe(content);

    return () => {
      if (!content) return;
      resizeObserver.unobserve(content);
    };
  }, [contentWrapper, resizeObserver]);
};
