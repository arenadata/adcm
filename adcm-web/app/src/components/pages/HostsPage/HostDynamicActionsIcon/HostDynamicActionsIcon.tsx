import type React from 'react';
import { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import type { AdcmHost } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import type { IconProps } from '@uikit/Icon/Icon';
import { openHostDynamicActionDialog } from '@store/adcm/hosts/hostsDynamicActionsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

interface HostDynamicActionsButtonProps {
  host: AdcmHost;
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const HostDynamicActionsIcon: React.FC<HostDynamicActionsButtonProps> = ({ host, type = 'icon', size }) => {
  const dispatch = useDispatch();

  const isDisabled = useMemo(() => isBlockingConcernPresent(host.concerns), [host.concerns]);

  const hostsDynamicActions = useStore((s) => s.adcm.hostsDynamicActions.hostDynamicActions[host.id] ?? null);

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
