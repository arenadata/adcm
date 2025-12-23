import type { ComponentProps, HTMLAttributes } from 'react';
import type React from 'react';
import { useEffect, useState } from 'react';
import cn from 'classnames';
import LeftBarMenu from '@commonComponents/LeftBarMenu/LeftBarMenu';
import LeftBarMenuItem from '@commonComponents/LeftBarMenu/LeftBarMenuItem';
import MainLogo from '@layouts/partials/MainLogo/MainLogo';
import s from './LeftSideBar.module.scss';
import { useDispatch, useStore, useMediaQuery, useLocalStorage } from '@hooks';
import { logout } from '@store/authSlice';
import { getAdcmSettings } from '@store/adcm/settings/settingsSlice';
import { isIssueConcernPresent } from '@utils/concernUtils';
import { IconButton } from '@uikit';
import { sideBarTopGroup } from '@layouts/partials/LeftSideBar/LeftSideBar.schema.ts';

const LeftSideBar: React.FC<HTMLAttributes<HTMLDivElement>> = ({ className }) => {
  const dispatch = useDispatch();
  const { username, firstName } = useStore((s) => s.auth.profile);
  const { adcmSettings } = useStore((s) => s.adcm.adcmSettings);

  const [isSmallScreen, setIsSmallScreen] = useState(false);

  const [isToggled, saveIsToggled] = useLocalStorage<boolean>({ key: 'isMenuToggled', initData: isSmallScreen });

  const [hasSettingsIssue, setHasSettingsIssue] = useState(false);

  useEffect(() => {
    if (adcmSettings) {
      setHasSettingsIssue(isIssueConcernPresent(adcmSettings.concerns));
    }
  }, [adcmSettings]);

  useEffect(() => {
    dispatch(getAdcmSettings());
  }, [dispatch]);

  useMediaQuery('(max-width: 1365px)', setIsSmallScreen);

  const isSlimMenu = isSmallScreen || isToggled === null ? isSmallScreen : isToggled;

  const handleToggleMenu = () => {
    saveIsToggled(!isToggled);
  };

  return (
    <div className={cn(s.leftSideBar, className)}>
      <div className={cn(s.leftSideBar__contentWrapper, { [s.leftSideBar__contentWrapper_slim]: isSlimMenu })}>
        <MainLogo className={s.leftSideBar__logo} isSmall={isSlimMenu} data-test="nav-menu-logo" />
        {!isSmallScreen && (
          <IconButton
            className={cn(s.leftSideBar__toggleBtn, { [s.leftSideBar__toggleBtn_reversed]: isSlimMenu })}
            variant="tertiary"
            icon="chevron"
            size={12}
            onClick={handleToggleMenu}
          />
        )}
        <LeftBarMenu className={cn(s.leftSideBar__menu, s.leftSideBar__menu_main)} data-test="nav-menu-pages">
          {sideBarTopGroup.map((sideBarItem) => (
            <LeftBarMenuItem key={sideBarItem.label} icon={sideBarItem.icon} to={sideBarItem.link} isSmall={isSlimMenu}>
              {sideBarItem.label}
            </LeftBarMenuItem>
          ))}
        </LeftBarMenu>

        <LeftBarMenu className={s.leftSideBar__menu} data-test="nav-menu-settings">
          <LeftBarMenuItem icon="g2-user" to="/profile" isSmall={isSlimMenu}>
            <div className={s.leftSideBar__userName}>{firstName || username}</div>
          </LeftBarMenuItem>
          <LeftBarMenuItem
            icon="g2-configuration"
            to="/settings"
            isSmall={isSlimMenu}
            variant={hasSettingsIssue ? 'alert' : 'default'}
          >
            Settings
          </LeftBarMenuItem>
          <LogoutMenuItem isSmall={isSlimMenu} />
        </LeftBarMenu>
      </div>
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
