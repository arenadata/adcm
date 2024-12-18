import type { SyncScrollPaneOptions } from './ScrollPane.types';

export const syncScrollPosition = (scrolledPane: HTMLElement, pane: HTMLElement, options: SyncScrollPaneOptions) => {
  const { scrollTop, scrollHeight, clientHeight, scrollLeft, scrollWidth, clientWidth } = scrolledPane;

  const scrollTopOffset = scrollHeight - clientHeight;
  const scrollLeftOffset = scrollWidth - clientWidth;

  const { syncVertical, syncHorizontal } = options;

  if (syncVertical && scrollTopOffset > 0) {
    pane.scrollTop = scrollTop;
  }
  if (syncHorizontal && scrollLeftOffset > 0) {
    pane.scrollLeft = scrollLeft;
  }
};
