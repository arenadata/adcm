import React from 'react';
import { matchPath, NavLink, useLocation } from 'react-router-dom';
import s from './Tabs.module.scss';
import cn from 'classnames';

interface TabProps extends React.HTMLAttributes<HTMLAnchorElement> {
  to: string;
  subPattern?: string;
  disabled?: boolean;
}
const Tab: React.FC<TabProps> = ({ children, to, subPattern, disabled = false }) => {
  const { pathname } = useLocation();

  const tabClasses = cn(s.tab, {
    [s.tab_active]: isCurrentTab(pathname, to, subPattern),
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

const isCurrentTab = (pathname: string, to: string, subPattern?: string) => {
  if (matchPath(subPattern || '', pathname)) return true;

  // if `to` - is path of root then full compare with pathname
  if (to.startsWith('/')) {
    return to === pathname;
  }

  // if `to` - is relative link, check with end of pathname
  return pathname.endsWith(to);
};
