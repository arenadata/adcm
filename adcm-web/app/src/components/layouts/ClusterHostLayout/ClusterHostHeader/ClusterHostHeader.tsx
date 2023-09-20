import React from 'react';
import { ButtonGroup } from '@uikit';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import { useStore } from '@hooks';
import { orElseGet } from '@utils/checkUtils';
import HostName from '@commonComponents/Host/HostName/HostName';
import { Link } from 'react-router-dom';
import ClusterHostUnlinkButton from '../ClusterHostUnlinkButton/ClusterHostUnlinkButton';
import ClusterHostsDynamicActionsButton from '@pages/cluster/ClusterHosts/ClusterHostsDynamicActionsButton/ClusterHostsDynamicActionsButton';

const ClusterHostHeader: React.FC = () => {
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const clusterHost = useStore(({ adcm }) => adcm.clusterHost.clusterHost);
  const successfulHostComponentsCount = useStore(
    ({ adcm }) => adcm.clusterHost.hostComponentsCounters.successfulHostComponentsCount,
  );
  const totalHostComponentsCount = useStore(
    ({ adcm }) => adcm.clusterHost.hostComponentsCounters.totalHostComponentsCount,
  );

  return (
    <EntityHeader
      title={orElseGet(clusterHost, (clusterHost) => (
        <HostName host={clusterHost} />
      ))}
      subtitle={orElseGet(clusterHost, (clusterHost) => (
        <Link className="text-link" to={`/hostproviders/${clusterHost.hostprovider.id}`}>
          {clusterHost.prototype.displayName} {clusterHost.prototype.version}
        </Link>
      ))}
      central={
        <div>
          {successfulHostComponentsCount} / {totalHostComponentsCount} successful components
        </div>
      }
      actions={
        <ButtonGroup>
          {cluster && clusterHost && <ClusterHostsDynamicActionsButton cluster={cluster} host={clusterHost} />}
          <ClusterHostUnlinkButton />
        </ButtonGroup>
      }
    />
  );
};

export default ClusterHostHeader;
