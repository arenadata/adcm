import { useState, useCallback, useEffect } from 'react';
import type { RefObject } from 'react';

export const useFullscreen = (elementRef: RefObject<HTMLElement>) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const enterFullscreen = useCallback(async () => {
    if (!elementRef.current) return;

    try {
      const isCurrentlyFullscreen = document.fullscreenElement;

      if (isCurrentlyFullscreen) {
        return;
      }

      const element = elementRef.current;
      const requestFullscreen = element.requestFullscreen;

      if (requestFullscreen) {
        await requestFullscreen.call(element);
        setIsFullscreen(true);
      }
    } catch (error) {
      console.warn('Failed to enter fullscreen:', error);
    }
  }, [elementRef]);

  const exitFullscreen = useCallback(async () => {
    try {
      const exitFullscreen = document.exitFullscreen;

      if (exitFullscreen) {
        await exitFullscreen.call(document);
        setIsFullscreen(false);
      }
    } catch (error) {
      console.warn('Failed to exit fullscreen:', error);
    }
  }, []);

  const toggleFullscreen = useCallback(() => {
    isFullscreen ? exitFullscreen() : enterFullscreen();
  }, [isFullscreen, enterFullscreen, exitFullscreen]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      const isCurrentlyFullscreen = Boolean(document.fullscreenElement);
      setIsFullscreen(isCurrentlyFullscreen);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  return {
    isFullscreen,
    toggleFullscreen,
  };
};
