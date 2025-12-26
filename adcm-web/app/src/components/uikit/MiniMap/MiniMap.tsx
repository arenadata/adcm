import type React from 'react';
import { useEffect, useRef, useState, useCallback } from 'react';
import s from './MiniMap.module.scss';
import { scaleFactor, caretThickness, minimapPadding } from './MiniMap.constants';
import {
  getMinimapWrapperHeight,
  getMinimapProportionalOffset,
  getContentVisibleRect,
  getButtonOffset,
} from './MiniMap.utils';
import { useResizeObserver } from '@hooks';
import Button from '@uikit/Button/Button';

interface MiniMapProps {
  scrollableWrapperRef: React.RefObject<HTMLDivElement>;
  contentWrapperRef: React.RefObject<HTMLDivElement>;
  children: React.ReactElement;
  minimapTopOffset?: number;
}

const MiniMap = ({ scrollableWrapperRef, children, contentWrapperRef, minimapTopOffset = 0 }: MiniMapProps) => {
  const [isMinimapVisible, setIsMinimapVisible] = useState(true);
  const [isMouseHold, setIsMouseHold] = useState(false);
  const [componentContent, setComponentContent] = useState<{ __html: string | TrustedHTML } | undefined>();
  const caretRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const coverRef = useRef<HTMLDivElement>(null);
  const minimapWrapperRef = useRef<HTMLDivElement>(null);
  const minimapContentWrapperRef = useRef<HTMLDivElement>(null);

  const updateMinimap = useCallback(() => {
    if (
      !contentWrapperRef.current ||
      !scrollableWrapperRef.current ||
      !minimapWrapperRef.current ||
      !buttonRef.current ||
      !coverRef.current ||
      !minimapContentWrapperRef.current
    ) {
      return;
    }

    if (contentWrapperRef.current.children[0]) {
      setComponentContent({ __html: contentWrapperRef.current.children[0].outerHTML });
    }

    const minimapContentHeight = contentWrapperRef.current.clientHeight * scaleFactor;

    minimapContentWrapperRef.current.style.height = `${minimapContentHeight}px`;
    coverRef.current.style.height = `${minimapContentHeight}px`;

    const minimapHeight = getMinimapWrapperHeight({
      contentWrapper: contentWrapperRef.current,
      scrollWrapper: scrollableWrapperRef.current,
      minimapTopOffset,
      minimapContentHeight,
      buttonOffset: getButtonOffset(buttonRef.current),
    });

    minimapWrapperRef.current.style.height = `${minimapHeight}px`;

    const contentTopOffset =
      contentWrapperRef.current.getBoundingClientRect().y -
      scrollableWrapperRef.current.getBoundingClientRect().y +
      scrollableWrapperRef.current.scrollTop;

    const wrapperMaxScroll =
      scrollableWrapperRef.current.scrollHeight -
      contentTopOffset -
      (scrollableWrapperRef.current.clientHeight - contentTopOffset);

    const minimapWrapperMaxScroll = minimapWrapperRef.current.scrollHeight;

    const wrapperRatio = (scrollableWrapperRef.current.scrollTop / wrapperMaxScroll) * 100;
    const minimapCurScrollTop = (minimapWrapperMaxScroll * wrapperRatio) / 100;

    const scrollY = minimapCurScrollTop - contentTopOffset > 0 ? minimapCurScrollTop - contentTopOffset : 0;
    minimapWrapperRef.current.scroll(0, scrollY);
  }, [contentWrapperRef.current, scrollableWrapperRef.current, minimapWrapperRef.current, isMinimapVisible]);

  const onResize = useCallback(() => {
    updateMinimap();
    caretUpdate();
  }, [updateMinimap]);

  const caretUpdate = () => {
    if (!caretRef.current || !contentWrapperRef.current || !scrollableWrapperRef.current) return;
    const originalContentHeight = getContentVisibleRect(contentWrapperRef.current);
    caretRef.current.style.height = `${originalContentHeight * scaleFactor + caretThickness * 2}px`;

    caretRef.current.style.top = `${
      getMinimapProportionalOffset(contentWrapperRef.current, scrollableWrapperRef.current) +
      (minimapPadding - caretThickness / 2)
    }px`;
  };

  const toggleMinimapVisibility = () => {
    setIsMinimapVisible((state) => !state);
  };

  const scrollToMousePosition = (e: React.MouseEvent<HTMLDivElement, globalThis.MouseEvent>) => {
    if (
      !coverRef.current ||
      !scrollableWrapperRef.current ||
      !contentWrapperRef.current ||
      !minimapWrapperRef.current
    ) {
      return;
    }

    const scrollPositionPercents =
      ((e.clientY - minimapWrapperRef.current.getBoundingClientRect().y) /
        (minimapWrapperRef.current.clientHeight - minimapPadding * 2)) *
      100;

    const contentTopOffset =
      contentWrapperRef.current.getBoundingClientRect().y -
      scrollableWrapperRef.current.getBoundingClientRect().y +
      scrollableWrapperRef.current.scrollTop;

    const wrapperMaxScroll =
      scrollableWrapperRef.current.scrollHeight -
      contentTopOffset -
      (scrollableWrapperRef.current.clientHeight - contentTopOffset);

    const minimapWrapperMaxScroll = minimapWrapperRef.current.scrollHeight;

    const minimapScrollYTo = (minimapWrapperMaxScroll * scrollPositionPercents) / 100;
    const contentWrapperScrollYTo = (wrapperMaxScroll * scrollPositionPercents) / 100;

    scrollableWrapperRef.current.scroll(0, contentWrapperScrollYTo + contentTopOffset);
    minimapWrapperRef.current.scroll(0, minimapScrollYTo);
  };

  const onMouseDown = (e: React.MouseEvent<HTMLDivElement, globalThis.MouseEvent>) => {
    setIsMouseHold(true);
    scrollToMousePosition(e);
  };

  const onMouseUp = () => {
    setIsMouseHold(false);
  };

  const onMouseMove = (e: React.MouseEvent<HTMLDivElement, globalThis.MouseEvent>) => {
    if (!isMouseHold) return;
    scrollToMousePosition(e);
  };

  const onMouseLeave = () => {
    setIsMouseHold(false);
  };

  useResizeObserver(contentWrapperRef, onResize);

  useEffect(() => {
    if (!scrollableWrapperRef.current) return;
    scrollableWrapperRef.current.addEventListener('scroll', onResize);

    return () => {
      if (!scrollableWrapperRef.current) return;
      scrollableWrapperRef.current.removeEventListener('scroll', onResize);
    };
  }, [scrollableWrapperRef.current]);

  return (
    <div className={s.minimapContainer}>
      <div className={s.minimapContentWrapper}>{children}</div>
      <div className={s.minimap} style={{ top: `${minimapTopOffset}px` }}>
        <Button
          ref={buttonRef}
          onClick={toggleMinimapVisibility}
          className={s.minimap_button}
          variant="tertiary"
          iconLeft="map"
        />
        {isMinimapVisible && (
          <div className={s.minimap_wrapper} draggable={false} ref={minimapWrapperRef}>
            <div ref={minimapContentWrapperRef} className={s.minimap_contentWrapper}>
              {/* biome-ignore lint/security/noDangerouslySetInnerHtml: only way to keep any component state in actual view */}
              <div className={s.minimap_content} draggable={false} dangerouslySetInnerHTML={componentContent} />
            </div>
            <div ref={caretRef} draggable={false} className={s.minimap_caret} />
            <div
              draggable={false}
              ref={coverRef}
              className={s.minimap_cover}
              onPointerDown={onMouseDown}
              onPointerUp={onMouseUp}
              onPointerMove={onMouseMove}
              onPointerLeave={onMouseLeave}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default MiniMap;
