import React, { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import { AdcmCluster } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import { openClusterDynamicActionDialog } from '@store/adcm/clusters/clustersDynamicActionsSlice';
import { IconProps } from '@uikit/Icon/Icon';

interface ClusterDynamicActionsButtonProps {
  cluster: AdcmCluster;
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const ClusterDynamicActionsIcon: React.FC<ClusterDynamicActionsButtonProps> = ({ cluster, type = 'icon', size }) => {
  const dispatch = useDispatch();

  const clusterDynamicActions = useStore(
    (s) => s.adcm.clustersDynamicActions.clusterDynamicActions[cluster.id] ?? null,
  );
  const isDisabled = useMemo(() => cluster.concerns.some(({ isBlocking }) => isBlocking), [cluster]);

  const handleSelectAction = (actionId: number) => {
    dispatch(openClusterDynamicActionDialog({ cluster, actionId }));
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={clusterDynamicActions}
      onSelectAction={handleSelectAction}
      disabled={isDisabled}
      size={size}
    />
  );
};

export default ClusterDynamicActionsIcon;
