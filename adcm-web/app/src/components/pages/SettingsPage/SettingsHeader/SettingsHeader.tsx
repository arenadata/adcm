import React from 'react';
import { BaseStatus, Statusable } from '@uikit';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import SettingsDynamicActionsIcon from './SettingsDynamicActionsIcon/SettingsDynamicActionsIcon';
import Concern from '@commonComponents/Concern/Concern';
import s from './SettingsHeader.module.scss';
import { useStore } from '@hooks';

const SettingsHeader: React.FC = () => {
  const adcmSettings = useStore((s) => s.adcm.adcmSettings.adcmSettings);

  return (
    <EntityHeader
      title={
        <div className={s.settingsHeader}>
          <SettingsDynamicActionsIcon />
          <Concern concerns={adcmSettings?.concerns ?? []} />
          <Statusable status={'unknown' as BaseStatus}>ADCM</Statusable>
        </div>
      }
    />
  );
};

export default SettingsHeader;
