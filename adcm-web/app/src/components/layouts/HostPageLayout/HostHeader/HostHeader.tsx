import type React from 'react';
import { ButtonGroup } from '@uikit';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import { useStore } from '@hooks';
import { orElseGet } from '@utils/checkUtils';
import HostName from '@commonComponents/host/HostName/HostName';
import { Link } from 'react-router-dom';
import HostDynamicActionsIcon from '@pages/HostsPage/HostDynamicActionsIcon/HostDynamicActionsIcon';
import HostUnlinkButton from '../Buttons/HostUnlinkButton/HostUnlinkButton';
import HostDeleteButton from '../Buttons/HostDeleteButton/HostDeleteButton';

const HostHeader: React.FC = () => {
  const host = useStore(({ adcm }) => adcm.host.host);
  const successfulHostComponentsCount = useStore(
    ({ adcm }) => adcm.host.hostComponentsCounters.successfulHostComponentsCount,
  );
  const totalHostComponentsCount = useStore(({ adcm }) => adcm.host.hostComponentsCounters.totalHostComponentsCount);

  return (
    <EntityHeader
      title={orElseGet(host, (host) => <HostName host={host} />)}
      central={orElseGet(host, (host) => (
        <>
          <Link className="text-link" to={`/hostproviders/${host.hostprovider.id}`}>
            {host.hostprovider.name}
          </Link>
          <span>
            {successfulHostComponentsCount} / {totalHostComponentsCount} successful components
          </span>
        </>
      ))}
      actions={
        <ButtonGroup>
          {host && <HostDynamicActionsIcon type="button" host={host} />}
          {host?.cluster ? <HostUnlinkButton /> : <HostDeleteButton />}
        </ButtonGroup>
      }
    />
  );
};

export default HostHeader;
