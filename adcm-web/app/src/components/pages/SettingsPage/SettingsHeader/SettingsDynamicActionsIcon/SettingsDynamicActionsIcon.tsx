import React from 'react';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import { IconProps } from '@uikit/Icon/Icon';

interface SettingsDynamicActionsButtonProps {
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const SettingsDynamicActionsButton: React.FC<SettingsDynamicActionsButtonProps> = ({ type = 'button', size }) => {
  const isDisabled = true;

  const handleSelectAction = () => {
    console.info('handleSelectAction');
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return <DynamicActionsTrigger actions={[]} onSelectAction={handleSelectAction} disabled={isDisabled} size={size} />;
};

export default SettingsDynamicActionsButton;
