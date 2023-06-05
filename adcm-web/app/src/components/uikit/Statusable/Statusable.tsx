import React from 'react';
import { Size } from '@uikit/utils/types';
import cn from 'classnames';
import s from './Statusable.module.scss';
import { BaseStatus } from './Statusable.types';

interface StatusableProps extends React.HTMLAttributes<HTMLDivElement> {
  status: BaseStatus;
  size?: Size;
}
const Statusable: React.FC<StatusableProps> = ({ children, className, status, size = 'small', ...props }) => {
  const classes = cn(className, s.statusable, s[`statusable_${size}`], s[`statusable_${status.toLowerCase()}`]);
  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
};
export default Statusable;
