import type React from 'react';
import { useRef } from 'react';
import { SyncScrollContext, type SyncScrollContextProps } from './SyncScroll.context';
import { syncScrollPosition } from './SyncScroll.utils';
import type { SyncScrollPaneOptions } from './ScrollPane.types';

type PaneState = {
  pane: HTMLElement;
  options: SyncScrollPaneOptions;
  isDisableScroll: boolean;
};

const SyncScrollContextProvider = ({ children }: React.PropsWithChildren) => {
  const panes = useRef<Map<string, PaneState>>(new Map());

  const syncOtherPanes = (scrolledPane: HTMLElement) => {
    const scrolledPaneId = scrolledPane.dataset.scrollpaneid!;

    if (panes.current.get(scrolledPaneId)?.isDisableScroll) {
      return;
    }

    for (const [paneId, state] of panes.current) {
      if (paneId !== scrolledPaneId) {
        state.isDisableScroll = true;
      }
    }

    if (scrolledPane) {
      window.requestAnimationFrame(() => {
        for (const [paneId, { pane, options }] of panes.current) {
          if (paneId !== scrolledPaneId) {
            syncScrollPosition(scrolledPane, pane, options);
          }
        }
      });
    }
  };

  const handlePaneScroll = (e: Event) => {
    syncOtherPanes(e.target as HTMLElement);
  };

  const handlePaneScrollEnd = (e: Event) => {
    syncOtherPanes(e.target as HTMLElement);

    for (const [, state] of panes.current) {
      state.isDisableScroll = false;
    }
  };

  const handleObservePane = (pane: HTMLElement, options: SyncScrollPaneOptions) => {
    const paneId = pane.dataset.scrollpaneid;

    if (!paneId) return;

    if (!panes.current.has(paneId)) {
      panes.current.set(paneId, { pane, options, isDisableScroll: false });
      pane.addEventListener('scroll', handlePaneScroll);
      pane.addEventListener('scrollend', handlePaneScrollEnd);
    }
  };

  const handleUnobservePane = (pane: HTMLElement) => {
    const paneId = pane.dataset.scrollpaneid;

    if (!paneId) return;

    if (panes.current.has(paneId)) {
      pane.removeEventListener('scroll', handlePaneScroll);
      pane.removeEventListener('scrollend', handlePaneScrollEnd);
      panes.current.delete(paneId);
    }
  };

  const contextValue: SyncScrollContextProps = {
    observePane: handleObservePane,
    unobservePane: handleUnobservePane,
  };

  return <SyncScrollContext.Provider value={contextValue}>{children}</SyncScrollContext.Provider>;
};

export default SyncScrollContextProvider;
