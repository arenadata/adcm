import React, { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import { AdcmCluster, AdcmService } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import { IconProps } from '@uikit/Icon/Icon';
import { openClusterServiceDynamicActionDialog } from '@store/adcm/cluster/services/servicesDynamicActionsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

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

  const idDisabled = useMemo(() => isBlockingConcernPresent(service.concerns), [service.concerns]);

  const serviceDynamicActions = useStore(
    (s) => s.adcm.servicesDynamicActions.serviceDynamicActions[service.id] ?? null,
  );

  const handleSelectAction = (actionId: number) => {
    dispatch(openClusterServiceDynamicActionDialog({ cluster, service, actionId }));
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={serviceDynamicActions}
      onSelectAction={handleSelectAction}
      disabled={idDisabled}
      size={size}
    />
  );
};

export default ClusterServiceDynamicActionsButton;
