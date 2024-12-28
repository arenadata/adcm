import React, { useEffect, useRef, forwardRef } from 'react';
import { useForwardRef } from '@hooks';
import { useSyncScrollContext } from './SyncScroll.context';
import s from './ScrollPane.module.scss';
import cn from 'classnames';

export interface ScrollPaneProps {
  children: React.ReactElement;
  hideScrollBars?: boolean;
  syncVertical?: boolean;
  syncHorizontal?: boolean;
}

const ScrollPane = forwardRef(
  ({ children, hideScrollBars, syncHorizontal = true, syncVertical = true }: ScrollPaneProps, ref) => {
    const { observePane, unobservePane } = useSyncScrollContext();

    const localRef = useRef<HTMLElement>(null);
    const inputRef = useForwardRef(ref, localRef);

    useEffect(() => {
      const instance = localRef.current;
      instance && observePane(instance, { syncHorizontal, syncVertical });
      return () => {
        instance && unobservePane(instance);
      };
    }, [localRef, observePane, unobservePane, syncHorizontal, syncVertical]);

    const className = cn(s.scrollPane, children.props.className, {
      [s.scrollPane_withoutScrollBars]: hideScrollBars,
      scroll: !hideScrollBars,
    });

    const clonedChildren = React.cloneElement(React.Children.only(children), { ref: inputRef, className });
    return clonedChildren;
  },
);

export default ScrollPane;
