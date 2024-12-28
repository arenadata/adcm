import type React from 'react';
import cn from 'classnames';
import s from './Tabs.module.scss';
import type { TabButtonProps } from './Tab.types';

const TabButton: React.FC<TabButtonProps> = ({ children, isActive, className, ...props }) => {
  const tabClasses = cn(s.tab, className, {
    active: isActive,
  });

  if (isActive) {
    return <div className={tabClasses}>{children}</div>;
  }

  return (
    <button className={tabClasses} {...props}>
      {children}
    </button>
  );
};

export default TabButton;
