import React, { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import { AdcmHostProvider } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import { IconProps } from '@uikit/Icon/Icon';
import { openHostProviderDynamicActionDialog } from '@store/adcm/hostProviders/hostProvidersDynamicActionsSlice';

interface HostProviderDynamicActionsButtonProps {
  hostProvider: AdcmHostProvider;
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const HostProviderDynamicActionsButton: React.FC<HostProviderDynamicActionsButtonProps> = ({
  hostProvider,
  type = 'button',
  size,
}) => {
  const dispatch = useDispatch();

  const dynamicActions = useStore(
    (s) => s.adcm.hostProvidersDynamicActions.hostProviderDynamicActions[hostProvider.id] ?? null,
  );
  const isDisabled = useMemo(() => hostProvider.concerns.some(({ isBlocking }) => isBlocking), [hostProvider]);

  const handleSelectAction = (actionId: number) => {
    dispatch(openHostProviderDynamicActionDialog({ hostProvider, actionId }));
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={dynamicActions}
      onSelectAction={handleSelectAction}
      disabled={isDisabled}
      size={size}
    />
  );
};

export default HostProviderDynamicActionsButton;
