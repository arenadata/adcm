import type React from 'react';
import { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import type { AdcmHostProvider } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import type { IconProps } from '@uikit/Icon/Icon';
import { openHostProviderDynamicActionDialog } from '@store/adcm/hostProviders/hostProvidersDynamicActionsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

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

  const idDisabled = useMemo(() => isBlockingConcernPresent(hostProvider.concerns), [hostProvider.concerns]);

  const dynamicActions = useStore(
    (s) => s.adcm.hostProvidersDynamicActions.hostProviderDynamicActions[hostProvider.id] ?? null,
  );

  const handleSelectAction = (actionId: number) => {
    dispatch(openHostProviderDynamicActionDialog({ hostProvider, actionId }));
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={dynamicActions}
      onSelectAction={handleSelectAction}
      disabled={idDisabled}
      size={size}
    />
  );
};

export default HostProviderDynamicActionsButton;
