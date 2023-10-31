import React from 'react';
import ClusterHostComponents from '@pages/cluster/host/HostComponents/HostComponents';
import { useStore } from '@hooks';
import { Spinner, Text } from '@uikit';
import { Link } from 'react-router-dom';

const HostComponents: React.FC = () => {
  const host = useStore(({ adcm }) => adcm.host.host);
  const isLoading = useStore(({ adcm }) => adcm.host.isLoading);

  if (isLoading) {
    return (
      <div>
        <Spinner />
      </div>
    );
  }

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
