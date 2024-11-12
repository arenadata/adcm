import React from 'react';
import Statusable from '@uikit/Statusable/Statusable';
import type { AdcmHost } from '@models/adcm';
import { hostStatusesMap } from '@pages/HostsPage/HostsTable/HostsTable.constants';

interface HostNameProps {
  host: AdcmHost;
}

const HostName: React.FC<HostNameProps> = ({ host }) => {
  return (
    <Statusable status={hostStatusesMap[host.status]} size="medium">
      {host.name}
    </Statusable>
  );
};

export default HostName;
