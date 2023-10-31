import React from 'react';
import SettingsHeader from './SettingsHeader/SettingsHeader';
import SettingsConfiguration from './SettingsConfiguration/SettingsConfiguration';
import { useRequestAdcmSettings } from '@pages/SettingsPage/useRequestAdcmSettings';

const SettingsPage: React.FC = () => {
  useRequestAdcmSettings();

  return (
    <div>
      <SettingsHeader />
      <SettingsConfiguration />
    </div>
  );
};

export default SettingsPage;
