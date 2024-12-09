import type React from 'react';
import { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import type { AdcmCluster, AdcmClusterHost } from '@models/adcm';
import { DynamicActionsButton, DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import type { IconProps } from '@uikit/Icon/Icon';
import { openClusterHostDynamicActionDialog } from '@store/adcm/cluster/hosts/hostsDynamicActionsSlice';
import { isBlockingConcernPresent } from '@utils/concernUtils';

interface ClusterHostsDynamicActionsButtonProps {
  cluster: AdcmCluster;
  host: AdcmClusterHost;
  size?: IconProps['size'];
  type?: 'button' | 'icon';
}

const ClusterHostsDynamicActionsButton: React.FC<ClusterHostsDynamicActionsButtonProps> = ({
  cluster,
  host,
  type = 'button',
  size,
}) => {
  const dispatch = useDispatch();

  const clusterHostsDynamicActions = useStore(
    (s) => s.adcm.clusterHostsDynamicActions.clusterHostDynamicActions[host.id] ?? null,
  );

  const isDisabled = useMemo(() => isBlockingConcernPresent(host.concerns), [host.concerns]);

  const handleSelectAction = (actionId: number) => {
    dispatch(openClusterHostDynamicActionDialog({ cluster, host, actionId }));
  };

  const DynamicActionsTrigger = type === 'icon' ? DynamicActionsIcon : DynamicActionsButton;

  return (
    <DynamicActionsTrigger
      actions={clusterHostsDynamicActions}
      onSelectAction={handleSelectAction}
      disabled={isDisabled}
      size={size}
    />
  );
};

export default ClusterHostsDynamicActionsButton;
