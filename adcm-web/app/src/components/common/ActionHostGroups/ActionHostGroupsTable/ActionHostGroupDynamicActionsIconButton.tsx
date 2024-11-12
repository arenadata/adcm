import React from 'react';
import type { AdcmDynamicAction } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import type { IconProps } from '@uikit/Icon/Icon';

interface ActionHostGroupDynamicActionsIconButtonProps {
  isDisabled?: boolean;
  dynamicActions: AdcmDynamicAction[];
  size?: IconProps['size'];
  type?: 'button' | 'icon';
  onActionSelect: (actionId: number) => void;
}

const ActionHostGroupDynamicActionsIconButton: React.FC<ActionHostGroupDynamicActionsIconButtonProps> = ({
  isDisabled,
  dynamicActions,
  type = 'icon',
  size,
  onActionSelect,
}) => {
  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger actions={dynamicActions} onSelectAction={onActionSelect} disabled={isDisabled} size={size} />
  );
};

export default ActionHostGroupDynamicActionsIconButton;
