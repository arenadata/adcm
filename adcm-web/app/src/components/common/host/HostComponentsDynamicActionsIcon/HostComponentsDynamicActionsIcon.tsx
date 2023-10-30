import React, { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import { AdcmServiceComponent } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import { IconProps } from '@uikit/Icon/Icon';
import { openClusterHostComponentDynamicActionDialog } from '@store/adcm/cluster/hosts/host/hostComponentsDynamicActionsSlice';

interface ClusterHostComponentsDynamicActionsIconProps {
  hostId: number;
  component: AdcmServiceComponent;
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const HostComponentsDynamicActionsIcon: React.FC<ClusterHostComponentsDynamicActionsIconProps> = ({
  component,
  hostId,
  type = 'icon',
  size,
}) => {
  const dispatch = useDispatch();

  const clusterHostComponentsDynamicActions = useStore(
    (s) => s.adcm.hostComponentsDynamicActions.hostComponentDynamicActions[component.prototype.id] ?? null,
  );
  const isDisabled = useMemo(() => component.concerns.some(({ isBlocking }) => isBlocking), [component]);

  const handleSelectAction = (actionId: number) => {
    dispatch(
      openClusterHostComponentDynamicActionDialog({
        clusterId: component.cluster.id,
        hostId,
        actionId,
      }),
    );
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={clusterHostComponentsDynamicActions}
      onSelectAction={handleSelectAction}
      disabled={isDisabled}
      size={size}
    />
  );
};

export default HostComponentsDynamicActionsIcon;
