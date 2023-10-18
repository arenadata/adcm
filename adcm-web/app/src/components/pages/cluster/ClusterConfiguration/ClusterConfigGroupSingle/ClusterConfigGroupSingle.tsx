import React from 'react';
import ConfigGroupSingleHeader from '@commonComponents/configGroups/ConfigGroupSingleHeader/ConfigGroupSingleHeader';
import { useClusterConfigGroupSingle } from '@pages/cluster/ClusterConfiguration/ClusterConfigGroupSingle/useClusterConfigGroupSingle';
import { useStore } from '@hooks';
import ClusterConfigGroupConfiguration from './ClusterConfigGroupConfiguration/ClusterConfigGroupConfiguration';

const ClusterConfigGroupSingle: React.FC = () => {
  const cluster = useStore((s) => s.adcm.cluster.cluster);

  useClusterConfigGroupSingle();
  const clusterConfigGroup = useStore((s) => s.adcm.clusterConfigGroup.clusterConfigGroup);

  return (
    <>
      <ConfigGroupSingleHeader
        configGroup={clusterConfigGroup}
        returnUrl={`/clusters/${cluster?.id}/configuration/config-groups`}
      />
      <ClusterConfigGroupConfiguration />
    </>
  );
};

export default ClusterConfigGroupSingle;
