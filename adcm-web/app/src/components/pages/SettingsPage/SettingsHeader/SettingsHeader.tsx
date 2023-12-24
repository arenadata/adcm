import React from 'react';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import SettingsDynamicActionsIcon from './SettingsDynamicActionsIcon/SettingsDynamicActionsIcon';
import Concern from '@commonComponents/Concern/Concern';
import s from './SettingsHeader.module.scss';
import { useStore } from '@hooks';
import { Text } from '@uikit';

const SettingsHeader: React.FC = () => {
  const adcmSettings = useStore((s) => s.adcm.adcmSettings.adcmSettings);

  return (
    <EntityHeader
      title={
        <div className={s.settingsHeader}>
          <SettingsDynamicActionsIcon />
          <Concern concerns={adcmSettings?.concerns ?? []} size={28} />
          <Text className={s.settingsHeader__text} variant="h3">
            ADCM
          </Text>
        </div>
      }
    />
  );
};

export default SettingsHeader;
