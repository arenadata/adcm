import React from 'react';
import SettingsHeader from './SettingsHeader/SettingsHeader';
import SettingsConfiguration from './SettingsConfiguration/SettingsConfiguration';
import { useRequestAdcmSettings } from '@pages/SettingsPage/useRequestAdcmSettings';
import SettingsDynamicActionDialog from '@pages/SettingsPage/SettingsDynamicActionDialog/SettingsDynamicActionDialog';

const SettingsPage: React.FC = () => {
  useRequestAdcmSettings();

  return (
    <div>
      <SettingsHeader />
      <SettingsConfiguration />
      <SettingsDynamicActionDialog />
    </div>
  );
};

export default SettingsPage;
