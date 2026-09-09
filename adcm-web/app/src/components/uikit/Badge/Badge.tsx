import type { HTMLAttributes } from 'react';
import type React from 'react';
import cn from 'classnames';
import type { BadgeStatus } from './Badge.types';
import s from './Badge.module.scss';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  status: BadgeStatus;
  truncate?: boolean;
}

const Badge: React.FC<BadgeProps> = ({ status, truncate = false, className, children, ...props }) => {
  return (
    <span className={cn(s.badge, s[`badge_${status}`], { [s.badge_truncate]: truncate }, className)} {...props}>
      <span className={s.badge__content}>{children}</span>
    </span>
  );
};

export default Badge;
