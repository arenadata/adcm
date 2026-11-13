import type { CSSProperties, Key, ReactNode } from 'react';
import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import cn from 'classnames';
import s from './VirtualList.module.scss';

const DEFAULT_ESTIMATE_SIZE = 24;
const DEFAULT_OVERSCAN = 5;

export interface VirtualListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => ReactNode;
  getItemKey?: (item: T, index: number) => Key;
  className?: string;
  contentClassName?: string;
  itemClassName?: string;
  style?: CSSProperties;
  estimateSize?: number;
  gap?: number;
  overscan?: number;
  measureItems?: boolean;
  emptyContent?: ReactNode;
  'data-test'?: string;
}

function VirtualList<T>({
  items,
  renderItem,
  getItemKey,
  className,
  contentClassName,
  itemClassName,
  style,
  estimateSize = DEFAULT_ESTIMATE_SIZE,
  gap = 0,
  overscan = DEFAULT_OVERSCAN,
  measureItems = true,
  emptyContent = null,
  'data-test': dataTest,
}: VirtualListProps<T>) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const initialHeight = typeof style?.height === 'number' ? style.height : undefined;

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => estimateSize,
    gap,
    overscan,
    initialRect: initialHeight !== undefined ? { width: 0, height: initialHeight } : undefined,
  });

  if (!items.length) {
    return emptyContent ? (
      <div className={className} style={style} data-test={dataTest}>
        {emptyContent}
      </div>
    ) : null;
  }

  const virtualItems = virtualizer.getVirtualItems();

  return (
    <div ref={scrollRef} className={cn(s.virtualList, className)} style={style} data-test={dataTest}>
      <div
        className={cn(s.virtualList__content, contentClassName)}
        style={{ height: `${virtualizer.getTotalSize()}px` }}
      >
        {virtualItems.map((virtualItem) => {
          const item = items[virtualItem.index];

          return (
            <div
              key={getItemKey?.(item, virtualItem.index) ?? virtualItem.key}
              ref={measureItems ? virtualizer.measureElement : undefined}
              data-index={virtualItem.index}
              className={cn(s.virtualList__item, itemClassName)}
              style={{
                height: measureItems ? undefined : `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              {renderItem(item, virtualItem.index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default VirtualList;
