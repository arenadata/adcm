import type React from 'react';
import { useState, useRef, useEffect, useCallback } from 'react';
import { SubJobsLogsAutoScrollContext, type SubJobsLogsAutoScrollOptions } from './SubJobLogsAutoScroll.context';
import { useResizeElementObserver } from '@hooks';

export interface SubJobLogsAutoScrollProviderProps extends React.PropsWithChildren {
  isInitialAutoScroll: boolean;
}

const SubJobLogsAutoScrollProvider = ({ isInitialAutoScroll, children }: SubJobLogsAutoScrollProviderProps) => {
  const [isAutoScroll, setIsAutoScroll] = useState(isInitialAutoScroll);

  const [containerElement, setContainerElement] = useState<HTMLElement | null>(null);

  const isResizeInProgressRef = useRef(false);
  const isAutoScrollStartedRef = useRef(false);
  const timer = useRef<number | null>(null);

  const handleResize = useCallback(() => {
    isResizeInProgressRef.current = true;
  }, []);

  const handleResizeComplete = useCallback(() => {
    isResizeInProgressRef.current = false;
  }, []);

  useResizeElementObserver(containerElement, handleResize, handleResizeComplete);

  useEffect(() => {
    const handleScroll = () => {
      setTimeout(() => {
        if (!isAutoScrollStartedRef.current && !isResizeInProgressRef.current) {
          setIsAutoScroll(false);
        }
      }, 100);
    };

    const handleScrollEnd = () => {
      setTimeout(() => {
        if (isAutoScrollStartedRef.current) {
          // handle end autoscroll
          isAutoScrollStartedRef.current = false;
        } else {
          // handle end user scroll
        }
      }, 200);
    };

    if (containerElement) {
      containerElement.addEventListener('scroll', handleScroll);
      containerElement.addEventListener('scrollend', handleScrollEnd);
    }

    return () => {
      containerElement?.removeEventListener('scroll', handleScroll);
      containerElement?.removeEventListener('scrollend', handleScrollEnd);
    };
  }, [containerElement]);

  useEffect(() => {
    return () => {
      if (!timer.current) return;
      window.clearTimeout(timer.current);
    };
  }, []);

  const scrollToBottom = useCallback(() => {
    if (!containerElement || !isAutoScroll) {
      return;
    }

    timer.current = window.setTimeout(() => {
      if (!isAutoScroll) return;

      requestAnimationFrame(() => {
        const isAlreadyScrolledToBottom =
          containerElement.scrollHeight - containerElement.scrollTop - containerElement.clientHeight < 1;

        if (!isAlreadyScrolledToBottom) {
          isAutoScrollStartedRef.current = true;
          containerElement?.scrollTo({ left: 0, top: containerElement.scrollHeight, behavior: 'smooth' });
        }
      });
    }, 250);
  }, [containerElement, isAutoScroll]);

  useEffect(() => {
    if (isAutoScroll) {
      scrollToBottom();
    }
  }, [containerElement, isAutoScroll]);

  const contextValue: SubJobsLogsAutoScrollOptions = {
    isAutoScroll,
    toggleAutoScroll: setIsAutoScroll,
    setContainer: setContainerElement,
    scrollToBottom,
  };

  return <SubJobsLogsAutoScrollContext.Provider value={contextValue}>{children}</SubJobsLogsAutoScrollContext.Provider>;
};

export default SubJobLogsAutoScrollProvider;
