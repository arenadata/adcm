import React from 'react';
import { Link, NavLink, resolvePath, useLocation } from 'react-router-dom';
import s from './Tabs.module.scss';
import cn from 'classnames';
import { isCurrentPathname } from '@utils/urlUtils';
import { TabProps } from '@uikit/Tabs/Tab.types';

const Tab: React.FC<TabProps> = ({ children, to, subPattern, disabled = false, isActive = false, onClick }) => {
  const { pathname } = useLocation();
  const resolvedPathname = resolvePath(to, pathname);

  const tabClasses = cn(s.tab, {
    [s.tab_active]: (to !== '' && isCurrentPathname(pathname, resolvedPathname, subPattern)) || isActive,
    [s.tab_disabled]: disabled,
  });

  return disabled ? (
    <div className={tabClasses}>{children}</div>
  ) : to === '' ? (
    <Link className={tabClasses} to={to} onClick={onClick}>
      {children}
    </Link>
  ) : (
    <NavLink className={tabClasses} to={to}>
      {children}
    </NavLink>
  );
};

export default Tab;
