import React from 'react';
import { DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';

const SettingsDynamicActionsButton: React.FC = () => {
  const isDisabled = true;

  const handleSelectAction = () => {
    console.info('handleSelectAction');
  };

  return <DynamicActionsIcon actions={[]} onSelectAction={handleSelectAction} disabled={isDisabled} />;
};

export default SettingsDynamicActionsButton;
