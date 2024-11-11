import React, { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import type { AdcmServiceComponent } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import type { IconProps } from '@uikit/Icon/Icon';
import { openClusterServiceComponentDynamicActionDialog } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsDynamicActionsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

interface ClusterServiceComponentsDynamicActionsIconProps {
  component: AdcmServiceComponent;
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const ServiceComponentsDynamicActionsIcon: React.FC<ClusterServiceComponentsDynamicActionsIconProps> = ({
  component,
  type = 'icon',
  size,
}) => {
  const dispatch = useDispatch();

  const isDisabled = useMemo(() => isBlockingConcernPresent(component.concerns), [component.concerns]);

  const clusterServiceComponentsDynamicActions = useStore(
    (s) => s.adcm.serviceComponentsDynamicActions.serviceComponentDynamicActions[component.id] ?? null,
  );

  const handleSelectAction = (actionId: number) => {
    dispatch(openClusterServiceComponentDynamicActionDialog({ component, actionId }));
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={clusterServiceComponentsDynamicActions}
      onSelectAction={handleSelectAction}
      disabled={isDisabled}
      size={size}
    />
  );
};

export default ServiceComponentsDynamicActionsIcon;
