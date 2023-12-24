import React from 'react';
import cn from 'classnames';
import s from '@uikit/Tabs/Tabs.module.scss';
import { TabButtonProps } from '@uikit/Tabs/Tab.types';

const TabButton: React.FC<TabButtonProps> = ({ children, isActive, className, ...props }) => {
  const tabClasses = cn(s.tab, className, {
    active: isActive,
  });

  return (
    <button className={tabClasses} {...props}>
      {children}
    </button>
  );
};

export default TabButton;
