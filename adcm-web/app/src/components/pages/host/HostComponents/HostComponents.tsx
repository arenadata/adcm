import React from 'react';
import ClusterHostComponents from '@pages/cluster/host/HostComponents/HostComponents';
import { useStore } from '@hooks';
import { Text } from '@uikit';
import { Link } from 'react-router-dom';

const HostComponents: React.FC = () => {
  const host = useStore(({ adcm }) => adcm.host.host);

  return host?.cluster ? (
    <ClusterHostComponents />
  ) : (
    <Text variant="h3">
      Please link the host to a cluster on the{' '}
      <Link className="text-link" to="/hosts">
        hosts page
      </Link>
    </Text>
  );
};

export default HostComponents;
