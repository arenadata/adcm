import React, { ComponentProps, HTMLAttributes, useState } from 'react';
import cn from 'classnames';
import LeftBarMenu from '@commonComponents/LeftBarMenu/LeftBarMenu';
import LeftBarMenuItem from '@commonComponents/LeftBarMenu/LeftBarMenuItem';
import MainLogo from '@layouts/partials/MainLogo/MainLogo';
import { useMediaQuery } from '@uikit/hooks/useMediaQuery';

import s from './LeftSideBar.module.scss';
import { useDispatch } from '@hooks';
import { logout } from '@store/authSlice';

const LeftSideBar: React.FC<HTMLAttributes<HTMLDivElement>> = ({ className }) => {
  const [isSlim, setIsSlim] = useState(false);

  useMediaQuery('(max-width: 980px)', setIsSlim);

  return (
    <div className={cn(s.leftSideBar, className)}>
      <MainLogo className={s.leftSideBar__logo} isSmall={isSlim} />

      <LeftBarMenu className={cn(s.leftSideBar__menu, s.leftSideBar__menu_main)}>
        <LeftBarMenuItem icon="g2-cluster3" to="/clusters" isSmall={isSlim}>
          Clusters
        </LeftBarMenuItem>
        <LeftBarMenuItem icon="g2-provider" to="/hostproviders" isSmall={isSlim}>
          Hostproviders
        </LeftBarMenuItem>
        <LeftBarMenuItem icon="g2-hosts" to="/hosts" isSmall={isSlim}>
          Hosts
        </LeftBarMenuItem>
        <LeftBarMenuItem icon="g2-jobs" to="/jobs" isSmall={isSlim}>
          Jobs
        </LeftBarMenuItem>
        <LeftBarMenuItem icon="g2-users" to="/access-manager" isSmall={isSlim}>
          Access manager
        </LeftBarMenuItem>
        <LeftBarMenuItem icon="g2-audit" to="/audit" isSmall={isSlim}>
          Audit
        </LeftBarMenuItem>
        <LeftBarMenuItem icon="g2-bundles" to="/bundles" isSmall={isSlim}>
          Bundles
        </LeftBarMenuItem>
      </LeftBarMenu>

      <LeftBarMenu className={s.leftSideBar__menu}>
        <LeftBarMenuItem icon="g2-user" to="/profile" isSmall={isSlim}>
          Admin
        </LeftBarMenuItem>
        <LeftBarMenuItem icon="g2-configuration" to="/settings" isSmall={isSlim}>
          Settings
        </LeftBarMenuItem>
        <LogoutMenuItem isSmall={isSlim} />
      </LeftBarMenu>
    </div>
  );
};
export default LeftSideBar;

const LogoutMenuItem: React.FC<Omit<ComponentProps<typeof LeftBarMenuItem>, 'icon' | 'onClick' | 'children'>> = (
  props,
) => {
  const dispatch = useDispatch();
  const handleLogout = () => {
    dispatch(logout());
  };

  return (
    <LeftBarMenuItem {...props} icon="g2-exit" onClick={handleLogout}>
      Log out
    </LeftBarMenuItem>
  );
};
