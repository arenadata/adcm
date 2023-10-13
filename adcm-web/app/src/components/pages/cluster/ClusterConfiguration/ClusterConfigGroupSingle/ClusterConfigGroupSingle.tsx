import React from 'react';
import ClusterConfigGroupSingleHeader from '@commonComponents/configGroups/ClusterConfigGroupSingleHeader/ClusterConfigGroupSingleHeader';
import { useClusterConfigGroupSingle } from '@pages/cluster/ClusterConfiguration/ClusterConfigGroupSingle/useClusterConfigGroupSingle';
import { useStore } from '@hooks';

const ClusterConfigGroupSingle: React.FC = () => {
  const cluster = useStore((s) => s.adcm.cluster.cluster);

  useClusterConfigGroupSingle();
  const clusterConfigGroup = useStore((s) => s.adcm.clusterConfigGroup.clusterConfigGroup);

  return (
    <>
      <ClusterConfigGroupSingleHeader
        configGroup={clusterConfigGroup}
        returnUrl={`/clusters/${cluster?.id}/configuration/config-groups`}
      />
    </>
  );
};

export default ClusterConfigGroupSingle;
