import React, { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { useDispatch, useStore } from '@hooks';
import { useRequestClusterServices } from './useRequestClusterServices';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import ClusterServicesTable from './ClusterServicesTable/ClusterServicesTable';
import ClusterServicesTableFooter from './ClusterServicesFooter/ClusterServicesTableFooter';
import ClusterServicesTableToolbar from './ClusterServicesToolbar/ClusterServicesTableToolbar';
import ClusterServiceActionsDialogs from './ClusterServiceActionsDialogs/ClusterServiceActionsDialogs';

const ClusterServices: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Services' },
        ]),
      );
    }
  }, [cluster, dispatch]);
  useRequestClusterServices();

  return (
    <TableContainer variant="easy">
      <ClusterServicesTableToolbar />
      <ClusterServicesTable />
      <ClusterServicesTableFooter />
      <ClusterServiceActionsDialogs />
    </TableContainer>
  );
};

export default ClusterServices;
