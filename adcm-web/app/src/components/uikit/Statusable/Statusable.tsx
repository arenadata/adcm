import React from 'react';
import cn from 'classnames';
import type { BaseStatus } from './Statusable.types';
import type { Size } from '@uikit/types/size.types';
import s from './Statusable.module.scss';

type StatusableIconPosition = 'left' | 'right';

interface StatusableProps extends React.HTMLAttributes<HTMLDivElement> {
  status: BaseStatus;
  size?: Size;
  iconPosition?: StatusableIconPosition;
}

const Statusable = React.forwardRef<HTMLDivElement, StatusableProps>(
  ({ children, className, status, size = 'small', iconPosition = 'right', ...props }, ref) => {
    const classes = cn(
      className,
      s.statusable,
      s[`statusable_${size}`],
      s[`statusable_${status.toLowerCase()}`],
      s[`statusable_${iconPosition}`],
    );
    return (
      <div className={classes} {...props} ref={ref}>
        {children}
      </div>
    );
  },
);

Statusable.displayName = 'Statusable';

export default Statusable;
