import React, { HTMLAttributes } from 'react';
import cn from 'classnames';
import s from './SubNavigationWrapper.module.scss';

const SubNavigationWrapper: React.FC<HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => {
  return (
    <div className={cn(className, s.subNavigationWrapper)} {...props}>
      {children}
    </div>
  );
};

export default SubNavigationWrapper;
