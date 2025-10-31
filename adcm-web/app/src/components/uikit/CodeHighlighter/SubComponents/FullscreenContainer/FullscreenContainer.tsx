import { createContext, type ReactNode, useContext, useRef } from 'react';
import IconButton from '@uikit/IconButton/IconButton';
import { useFullscreen } from '@hooks';
import cn from 'classnames';
import s from './FullscreenContainer.module.scss';

export interface FullscreenContainerProps {
  children: ReactNode;
  className?: string;
}

interface FullscreenContextValue {
  isFullscreen: boolean;
  toggleFullscreen: () => void;
}

const FullscreenContext = createContext<FullscreenContextValue | null>(null);

export const useFullscreenContext = () => useContext(FullscreenContext);

export const FullscreenContainer = ({ children, className }: FullscreenContainerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { isFullscreen, toggleFullscreen } = useFullscreen(containerRef);

  const contextValue: FullscreenContextValue = {
    isFullscreen,
    toggleFullscreen,
  };

  return (
    <FullscreenContext.Provider value={contextValue}>
      <div ref={containerRef} className={cn(className, { [s.fullscreenContainer_fullscreen]: isFullscreen })}>
        {isFullscreen && (
          <IconButton
            icon="g2-close"
            variant="secondary"
            size={24}
            className={s.fullscreenContainer__close}
            onClick={toggleFullscreen}
          />
        )}
        {children}
      </div>
    </FullscreenContext.Provider>
  );
};
