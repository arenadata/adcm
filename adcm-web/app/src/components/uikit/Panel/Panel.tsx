import React, { HTMLAttributes } from 'react';
import cn from 'classnames';
import s from './Panel.module.scss';

const Panel: React.FC<HTMLAttributes<HTMLDivElement>> = ({ className, children, ...props }) => {
  return (
    <div className={cn(s.panel, className)} {...props}>
      {children}
    </div>
  );
};

export default Panel;
