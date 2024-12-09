import type React from 'react';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import HostsTableToolbar from '@pages/HostsPage/HostsTableToolbar/HostsTableToolbar';
import HostsTable from '@pages/HostsPage/HostsTable/HostsTable';
import HostsTableFooter from '@pages/HostsPage/HostsTableFooter/HostsTableFooter';
import { useRequestHosts } from '@pages/HostsPage/useRequestHosts';
import HostsActionsDialogs from '@pages/HostsPage/HostsActionsDialogs/HostsActionsDialogs';

const HostsPage: React.FC = () => {
  useRequestHosts();

  return (
    <TableContainer variant="easy">
      <HostsTableToolbar />
      <HostsTable />
      <HostsTableFooter />
      <HostsActionsDialogs />
    </TableContainer>
  );
};

export default HostsPage;
