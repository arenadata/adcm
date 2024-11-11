import type { HTMLAttributes } from 'react';
import React from 'react';
import cn from 'classnames';
import s from './ButtonGroup.module.scss';

const ButtonGroup: React.FC<HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => {
  return (
    <div className={cn(className, s.buttonGroup)} {...props}>
      {children}
    </div>
  );
};
export default ButtonGroup;
