import type React from 'react';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import HostsTableFilters from '@pages/HostsPage/HostsTableToolbar/HostsTableFilters';
import ButtonGroup from '@uikit/ButtonGroup/ButtonGroup';
import HostsCreateHostButton from '@pages/HostsPage/HostsTableToolbar/HostsCreateHostButton/HostsCreateHostButton';
import HostsBulkOperationsButton from '@pages/HostsPage/HostsTableToolbar/HostsBulkOperationsButton/HostsBulkOperationsButton';

const HostsTableToolbar: React.FC = () => (
  <TableToolbar>
    <HostsTableFilters />
    <ButtonGroup>
      <HostsBulkOperationsButton />
      <HostsCreateHostButton />
    </ButtonGroup>
  </TableToolbar>
);

export default HostsTableToolbar;
