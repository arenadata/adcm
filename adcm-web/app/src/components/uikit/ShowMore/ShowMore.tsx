import type { CSSProperties, PropsWithChildren } from 'react';
import { useEffect, useRef, useState } from 'react';
import cn from 'classnames';
import s from './ShowMore.module.scss';

export interface ShowMoreProps extends PropsWithChildren {
  className?: string;
  maxLines?: number;
  showMoreLabel?: string;
  showLessLabel?: string;
}

const ShowMore = ({
  children,
  className,
  maxLines = 3,
  showMoreLabel = 'Show more',
  showLessLabel = 'Show less',
}: ShowMoreProps) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isOverflowing, setIsOverflowing] = useState(false);

  useEffect(() => {
    const content = contentRef.current;
    if (!content) return;

    const updateOverflow = () => {
      if (isExpanded) {
        return;
      }

      setIsOverflowing(content.scrollHeight > content.clientHeight + 1);
    };

    updateOverflow();

    const resizeObserver = new ResizeObserver(updateOverflow);
    resizeObserver.observe(content);

    return () => {
      resizeObserver.disconnect();
    };
  }, [children, isExpanded, maxLines]);

  const showToggle = isOverflowing || isExpanded;

  return (
    <div className={cn(s.showMore, className)} style={{ '--show-more-lines': maxLines } as CSSProperties}>
      <div ref={contentRef} className={cn(s.showMore__content, { [s.showMore__content_collapsed]: !isExpanded })}>
        {children}
      </div>
      {showToggle && (
        <button type="button" className={s.showMore__toggle} onClick={() => setIsExpanded((expanded) => !expanded)}>
          {isExpanded ? showLessLabel : showMoreLabel}
        </button>
      )}
    </div>
  );
};

export default ShowMore;
