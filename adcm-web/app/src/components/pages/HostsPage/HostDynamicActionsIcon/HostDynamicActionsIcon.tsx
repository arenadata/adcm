import React, { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import { AdcmHost } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import { IconProps } from '@uikit/Icon/Icon';
import { openHostDynamicActionDialog } from '@store/adcm/hosts/hostsDynamicActionsSlice';

interface HostDynamicActionsButtonProps {
  host: AdcmHost;
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const HostDynamicActionsIcon: React.FC<HostDynamicActionsButtonProps> = ({ host, type = 'icon', size }) => {
  const dispatch = useDispatch();

  const hostsDynamicActions = useStore((s) => s.adcm.hostsDynamicActions.hostDynamicActions[host.id] ?? null);
  const isDisabled = useMemo(() => host.concerns.some(({ isBlocking }) => isBlocking), [host]);

  const handleSelectAction = (actionId: number) => {
    dispatch(openHostDynamicActionDialog({ host, actionId }));
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={hostsDynamicActions}
      onSelectAction={handleSelectAction}
      disabled={isDisabled}
      size={size}
    />
  );
};

export default HostDynamicActionsIcon;
