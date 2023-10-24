import React from 'react';
import { BaseStatus, Statusable } from '@uikit';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import SettingsDynamicActionsIcon from './SettingsDynamicActionsIcon/SettingsDynamicActionsIcon';
import Concern from '@commonComponents/Concern/Concern';
import s from './SettingsHeader.module.scss';

const SettingsHeader: React.FC = () => {
  return (
    <EntityHeader
      title={
        <div className={s.settingsHeader}>
          <SettingsDynamicActionsIcon />
          <Concern concerns={[]} />
          <Statusable status={'unknown' as BaseStatus}>ADCM</Statusable>
        </div>
      }
    />
  );
};

export default SettingsHeader;
