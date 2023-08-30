import React, { useEffect } from 'react';
import ClusterHostsTableToolbar from '@pages/cluster/ClusterHosts/ClusterHostsTableToolbar/ClusterHostsTableToolbar';
import ClusterHostsActionsDialogs from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/ClusterHostsActionsDialogs';
import ClusterHostsTable from '@pages/cluster/ClusterHosts/ClusterHostsTable/ClusterHostsTable';
import ClusterHostsTableFooter from '@pages/cluster/ClusterHosts/ClusterHostsTableFooter/ClusterHostsTableFooter';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import { useRequestClusterHosts } from '@pages/cluster/ClusterHosts/useRequestClusterHosts';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

const ClusterHosts: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Hosts' },
        ]),
      );
    }
  }, [cluster, dispatch]);

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
