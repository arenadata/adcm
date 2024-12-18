import React, { useContext } from 'react';
import type { SyncScrollPaneOptions } from './ScrollPane.types';

export interface SyncScrollContextProps {
  observePane: (pane: HTMLElement, options: SyncScrollPaneOptions) => void;
  unobservePane: (pane: HTMLElement) => void;
}

export const SyncScrollContext = React.createContext<SyncScrollContextProps>({} as SyncScrollContextProps);

export const useSyncScrollContext = () => {
  const ctx = useContext<SyncScrollContextProps>(SyncScrollContext as React.Context<SyncScrollContextProps>);
  if (!ctx) {
    throw new Error('useContext must be inside a Provider with a value');
  }

  return ctx;
};
