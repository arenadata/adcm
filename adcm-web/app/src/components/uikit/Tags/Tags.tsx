import type { HTMLAttributes } from 'react';
import type React from 'react';
import s from './Tags.module.scss';
import cn from 'classnames';

const Tags: React.FC<HTMLAttributes<HTMLDivElement>> = ({ className, children, ...props }) => {
  return (
    <div className={cn(className, s.tags)} {...props}>
      {children}
    </div>
  );
};
export default Tags;
