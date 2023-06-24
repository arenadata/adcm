import React from 'react';
import { ReactComponent as Bell } from './images/complex-bell.svg';
import s from './HeaderNotifications.module.scss';
import iconButtonStyles from '@uikit/IconButton/IconButton.module.scss';
import cn from 'classnames';

const HeaderNotifications: React.FC = () => {
  // TODO: get status from store
  const status = 'error' as 'error' | 'success' | 'empty';

  const className = cn(s.headerNotifications, iconButtonStyles.iconButton, iconButtonStyles.iconButton_primary, {
    [s.headerNotifications_error]: status === 'error',
    [s.headerNotifications_success]: status === 'success',
  });

  return (
    <>
      <button className={className}>
        <Bell width={28} />
      </button>
    </>
  );
};

export default HeaderNotifications;
