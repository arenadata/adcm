import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import s from './Tabs.module.scss';
import cn from 'classnames';
import { isCurrentPathname } from '@uikit/utils/urlUtils';
import { TabProps } from '@uikit/Tabs/Tab.types';

const Tab: React.FC<TabProps> = ({ children, to, subPattern, disabled = false }) => {
  const { pathname } = useLocation();

  const tabClasses = cn(s.tab, {
    [s.tab_active]: isCurrentPathname(pathname, to, subPattern),
    [s.tab_disabled]: disabled,
  });
  return disabled ? (
    <div className={tabClasses}>{children}</div>
  ) : (
    <NavLink className={tabClasses} to={to}>
      {children}
    </NavLink>
  );
};
export default Tab;
