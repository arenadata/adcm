import React, { ComponentProps, HTMLAttributes, useEffect, useState } from 'react';
import cn from 'classnames';
import LeftBarMenu from '@commonComponents/LeftBarMenu/LeftBarMenu';
import LeftBarMenuItem from '@commonComponents/LeftBarMenu/LeftBarMenuItem';
import MainLogo from '@layouts/partials/MainLogo/MainLogo';
import s from './LeftSideBar.module.scss';
import { useDispatch, useStore, useMediaQuery } from '@hooks';
import { logout } from '@store/authSlice';
import { getAdcmSettings } from '@store/adcm/settings/settingsSlice.ts';
import { isBlockingConcernPresent } from '@utils/concernUtils.ts';

const LeftSideBar: React.FC<HTMLAttributes<HTMLDivElement>> = ({ className }) => {
  const dispatch = useDispatch();
  const { username, firstName } = useStore((s) => s.auth.profile);
  const { adcmSettings } = useStore((s) => s.adcm.adcmSettings);

  const [isSlim, setIsSlim] = useState(false);
  const [isConcernHasConflicts, setIsConcernHasConflicts] = useState(false);

  useEffect(() => {
    if (adcmSettings) {
      setIsConcernHasConflicts(isBlockingConcernPresent(adcmSettings.concerns));
    }
  }, [adcmSettings]);

  useEffect(() => {
    dispatch(getAdcmSettings());
  }, [dispatch]);

  useMediaQuery('(max-width: 980px)', setIsSlim);

  return (
    <div className={cn(s.leftSideBar, className)}>
      <MainLogo className={s.leftSideBar__logo} isSmall={isSlim} data-test="nav-menu-logo" />

      <LeftBarMenu className={cn(s.leftSideBar__menu, s.leftSideBar__menu_main)} data-test="nav-menu-pages">
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

      <LeftBarMenu className={s.leftSideBar__menu} data-test="nav-menu-settings">
        <LeftBarMenuItem icon="g2-user" to="/profile" isSmall={isSlim}>
          <div className={s.leftSideBar__userName}>{firstName || username}</div>
        </LeftBarMenuItem>
        <LeftBarMenuItem
          icon="g2-configuration"
          to="/settings"
          isSmall={isSlim}
          variant={isConcernHasConflicts ? 'alert' : 'default'}
        >
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
