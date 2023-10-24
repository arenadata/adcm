import React from 'react';
import SettingsHeader from './SettingsHeader/SettingsHeader';
import SettingsConfiguration from './SettingsConfiguration/SettingsConfiguration';

const SettingsPage: React.FC = () => {
  return (
    <div>
      <SettingsHeader />
      <SettingsConfiguration />
    </div>
  );
};

export default SettingsPage;
