import type React from 'react';
import { useRef } from 'react';
import { MiniMap } from '@uikit';
import { useMainLayoutMainContentRef } from '@hooks/useMainLayoutMainContentRef.ts';

const toolBarHeight = 88;

const ConfigurationMinimap = ({ children }: React.PropsWithChildren) => {
  const { wrapperRef } = useMainLayoutMainContentRef();
  const contentRef = useRef(null);

  return (
    <MiniMap scrollableWrapperRef={wrapperRef} contentWrapperRef={contentRef} minimapTopOffset={toolBarHeight}>
      <div ref={contentRef}>{children}</div>
    </MiniMap>
  );
};

export default ConfigurationMinimap;
