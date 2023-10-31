import React, { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import { AdcmCluster, AdcmService } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import { IconProps } from '@uikit/Icon/Icon';
import { openClusterServiceDynamicActionDialog } from '@store/adcm/cluster/services/servicesDynamicActionsSlice';

interface ClusterServiceDynamicActionsButtonProps {
  cluster: AdcmCluster;
  service: AdcmService;
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const ClusterServiceDynamicActionsButton: React.FC<ClusterServiceDynamicActionsButtonProps> = ({
  cluster,
  service,
  type = 'button',
  size,
}) => {
  const dispatch = useDispatch();

  const serviceDynamicActions = useStore(
    (s) => s.adcm.servicesDynamicActions.serviceDynamicActions[service.id] ?? null,
  );
  const isDisabled = useMemo(() => service.concerns.some(({ isBlocking }) => isBlocking), [service]);

  const handleSelectAction = (actionId: number) => {
    dispatch(openClusterServiceDynamicActionDialog({ cluster, service, actionId }));
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={serviceDynamicActions}
      onSelectAction={handleSelectAction}
      disabled={isDisabled}
      size={size}
    />
  );
};

export default ClusterServiceDynamicActionsButton;
