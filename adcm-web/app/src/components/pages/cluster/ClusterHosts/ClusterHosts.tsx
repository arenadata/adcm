import React from 'react';
import ClusterHostsTableToolbar from '@pages/cluster/ClusterHosts/ClusterHostsTableToolbar/ClusterHostsTableToolbar';
import ClusterHostsActionsDialogs from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/ClusterHostsActionsDialogs';
import ClusterHostsTable from '@pages/cluster/ClusterHosts/ClusterHostsTable/ClusterHostsTable';
import ClusterHostsTableFooter from '@pages/cluster/ClusterHosts/ClusterHostsTableFooter/ClusterHostsTableFooter';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import { useRequestClusterHosts } from '@pages/cluster/ClusterHosts/useRequestClusterHosts';

const ClusterHosts: React.FC = () => {
  useRequestClusterHosts();

  return (
    <TableContainer variant="subPage">
      <ClusterHostsTableToolbar />
      <ClusterHostsTable />
      <ClusterHostsTableFooter />
      <ClusterHostsActionsDialogs />
    </TableContainer>
  );
};

export default ClusterHosts;
