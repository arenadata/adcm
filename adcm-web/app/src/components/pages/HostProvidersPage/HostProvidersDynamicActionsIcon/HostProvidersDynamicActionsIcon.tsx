import React, { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import type { AdcmHostProvider } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import type { IconProps } from '@uikit/Icon/Icon';
import { openHostProviderDynamicActionDialog } from '@store/adcm/hostProviders/hostProvidersDynamicActionsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

interface HostProvidersDynamicActionsButtonProps {
  hostProvider: AdcmHostProvider;
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const HostProvidersDynamicActionsIcon: React.FC<HostProvidersDynamicActionsButtonProps> = ({
  hostProvider,
  type = 'icon',
  size,
}) => {
  const dispatch = useDispatch();

  const isDisabled = useMemo(() => isBlockingConcernPresent(hostProvider.concerns), [hostProvider.concerns]);

  const hostProvidersDynamicActions = useStore(
    (s) => s.adcm.hostProvidersDynamicActions.hostProviderDynamicActions[hostProvider.id] ?? null,
  );

  const handleSelectAction = (actionId: number) => {
    dispatch(openHostProviderDynamicActionDialog({ hostProvider, actionId }));
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={hostProvidersDynamicActions}
      onSelectAction={handleSelectAction}
      disabled={isDisabled}
      size={size}
    />
  );
};

export default HostProvidersDynamicActionsIcon;
