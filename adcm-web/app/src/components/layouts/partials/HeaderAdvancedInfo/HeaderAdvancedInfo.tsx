import React from 'react';
import HeaderHelp from '@layouts/partials/HeaderHelp/HeaderHelp';
import HeaderNotifications from '@layouts/partials/HeaderNotifications/HeaderNotifications';

import s from './HeaderAdvancedInfo.module.scss';

const HeaderAdvancedInfo: React.FC = () => {
  return (
    <div className={s.headerAdvancedInfo}>
      <HeaderNotifications />
      <HeaderHelp />
    </div>
  );
};

export default HeaderAdvancedInfo;
