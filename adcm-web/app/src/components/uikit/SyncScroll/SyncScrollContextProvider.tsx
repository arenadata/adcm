import type React from 'react';
import { useRef } from 'react';
import { SyncScrollContext, type SyncScrollContextProps } from './SyncScroll.context';
import { syncScrollPosition } from './SyncScroll.utils';
import type { SyncScrollPaneOptions } from './ScrollPane.types';

const SyncScrollContextProvider = ({ children }: React.PropsWithChildren) => {
  const panes = useRef<{ pane: HTMLElement; options: SyncScrollPaneOptions }[]>([]);

  const handlePaneScroll = (e: Event) => {
    const scrolledPane = e.target as HTMLElement;

    if (scrolledPane) {
      window.requestAnimationFrame(() => {
        for (let i = 0; i < panes.current.length; i++) {
          const { pane, options } = panes.current[i];
          if (scrolledPane !== pane) {
            /* Remove event listeners from the node before sync */
            pane.removeEventListener('scroll', handlePaneScroll);
            syncScrollPosition(scrolledPane, pane, options);
            /* Re-attach event listeners after we're done scrolling */
            window.requestAnimationFrame(() => {
              pane.addEventListener('scroll', handlePaneScroll);
            });
          }
        }
      });
    }
  };

  const handleObservePane = (pane: HTMLElement, options: SyncScrollPaneOptions) => {
    const alreadyObservedPane = panes.current.find((x) => x.pane === pane);
    if (!alreadyObservedPane) {
      panes.current.push({ pane, options });
      pane.addEventListener('scroll', handlePaneScroll);
    }
  };

  const handleUnobservePane = (pane: HTMLElement) => {
    const paneIndex = panes.current.findIndex((x) => x.pane === pane);
    if (paneIndex !== -1) {
      pane.removeEventListener('scroll', handlePaneScroll);
      panes.current.splice(paneIndex, 1);
    }
  };

  const contextValue: SyncScrollContextProps = {
    observePane: handleObservePane,
    unobservePane: handleUnobservePane,
  };

  return <SyncScrollContext.Provider value={contextValue}>{children}</SyncScrollContext.Provider>;
};

export default SyncScrollContextProvider;
