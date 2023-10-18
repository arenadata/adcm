import React from 'react';
import cn from 'classnames';
import { BaseStatus } from './Statusable.types';
import { Size } from '@uikit/types/size.types';
import s from './Statusable.module.scss';

interface StatusableProps extends React.HTMLAttributes<HTMLDivElement> {
  status: BaseStatus;
  size?: Size;
}

const Statusable = React.forwardRef<HTMLDivElement, StatusableProps>(
  ({ children, className, status, size = 'small', ...props }, ref) => {
    const classes = cn(className, s.statusable, s[`statusable_${size}`], s[`statusable_${status.toLowerCase()}`]);
    return (
      <div className={classes} {...props} ref={ref}>
        {children}
      </div>
    );
  },
);

Statusable.displayName = 'Statusable';

export default Statusable;
