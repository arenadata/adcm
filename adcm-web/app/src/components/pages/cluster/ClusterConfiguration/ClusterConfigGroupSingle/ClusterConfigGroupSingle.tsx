import type React from 'react';
import ConfigGroupSingleHeader from '@commonComponents/configGroups/ConfigGroupSingleHeader/ConfigGroupSingleHeader';
import { useClusterConfigGroupSingle } from '@pages/cluster/ClusterConfiguration/ClusterConfigGroupSingle/useClusterConfigGroupSingle';
import { useStore } from '@hooks';
import ClusterConfigGroupConfiguration from './ClusterConfigGroupConfiguration/ClusterConfigGroupConfiguration';
import EditConfigGroupDescriptionDialog from '@commonComponents/configGroups/EditConfigGroupDescriptionDialog/EditConfigGroupDescriptionDialog';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams.ts';

const ClusterConfigGroupSingle: React.FC = () => {
  const { clusterId } = useServiceComponentParams();

  useClusterConfigGroupSingle();
  const clusterConfigGroup = useStore((s) => s.adcm.clusterConfigGroup.clusterConfigGroup);

  return (
    <>
      <ConfigGroupSingleHeader
        configGroup={clusterConfigGroup}
        returnUrl={`/clusters/${clusterId}/configuration/config-groups`}
        entityType="cluster"
        entityArgs={{ clusterId }}
      />
      <ClusterConfigGroupConfiguration />
      <EditConfigGroupDescriptionDialog />
    </>
  );
};

export default ClusterConfigGroupSingle;
