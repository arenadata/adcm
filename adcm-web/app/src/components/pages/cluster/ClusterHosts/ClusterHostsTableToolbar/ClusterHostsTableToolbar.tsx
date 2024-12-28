import type React from 'react';
import { ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import ClusterHostsTableFilters from '@pages/cluster/ClusterHosts/ClusterHostsTableToolbar/ClusterHostsTableFilters';
import ClusterHostsAddHostsButton from '@pages/cluster/ClusterHosts/ClusterHostsTableToolbar/ClusterHostsAddHostsButton/ClusterHostsAddHostsButton';

const ClusterHostsTableToolbar: React.FC = () => (
  <TableToolbar>
    <ClusterHostsTableFilters />
    <ButtonGroup>
      <ClusterHostsAddHostsButton />
    </ButtonGroup>
  </TableToolbar>
);

export default ClusterHostsTableToolbar;
