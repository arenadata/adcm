import type { HTMLAttributes } from 'react';
import React, { useEffect, useState } from 'react';
import cn from 'classnames';
import s from './AnchorBar.module.scss';

export type AnchorBarItem = {
  label: string;
  id: string;
  activeColorClass?: string;
};

export interface AnchorListProps {
  items: AnchorBarItem[];
  className?: string;
}

export interface AnchorBarProps extends HTMLAttributes<HTMLDivElement> {
  dataTest?: string;
}

export const AnchorList = ({ items, className = '' }: AnchorListProps) => {
  const [activeItems, setActiveItems] = useState(new Set<string>());
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          setActiveItems((prev) => {
            if (entry.isIntersecting) {
              prev.add(entry.target.id);
            } else {
              prev.delete(entry.target.id);
            }

            return new Set([...prev]);
          });
        });
      },
      { threshold: 0.1 },
    );

    items.forEach((anchor) => {
      const el = document.getElementById(anchor.id);
      if (el) {
        observer.observe(el as Element);
      }
    });

    return () => {
      observer.disconnect();
    };
  }, [items]);

  const getHandleClick = (id: string) => (event: React.MouseEvent<HTMLElement>) => {
    event.preventDefault();
    scrollTo(id);
  };

  return (
    <ul className={cn(className, s.anchorBar__list)}>
      {items.map(({ label, id, activeColorClass = '' }) => {
        const linkClasses = cn(s.anchorBar__link, {
          [s.anchorBar__link_default]: !activeItems.has(id),
          [s.anchorBar__link_default_active]: !activeColorClass && activeItems.has(id),
          [activeColorClass]: !!(activeColorClass && activeItems.has(id)),
        });

        return (
          <li key={id}>
            <a className={linkClasses} href={`#${id}`} onClick={getHandleClick(id)}>
              {label}
            </a>
          </li>
        );
      })}
    </ul>
  );
};

const AnchorBar = ({ className, children, dataTest = 'anchor-bar', ...props }: AnchorBarProps) => {
  return (
    <aside className={cn(className, s.anchorBar)} data-test={dataTest} {...props}>
      {children}
    </aside>
  );
};

export default AnchorBar;

const scrollTo = (id: string) => {
  const el = document.getElementById(id);
  if (!el) return;

  el.scrollIntoView({
    behavior: 'smooth',
  });
};
