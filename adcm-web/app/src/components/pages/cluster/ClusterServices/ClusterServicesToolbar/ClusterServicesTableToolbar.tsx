import { Button } from '@uikit';
import ClusterServicesFilters from './ClusterServicesTableFilters';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import { useDispatch, useStore } from '@hooks';
import { openAddServicesDialog } from '@store/adcm/cluster/services/servicesActionsSlice';

const ClustersTableHeader = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const isAddingServices = useStore(({ adcm }) => adcm.servicesActions.isAddingServices);

  const handleAddClusterServiceClick = () => {
    dispatch(openAddServicesDialog());
  };

  return (
    <TableToolbar>
      <ClusterServicesFilters />
      <Button
        onClick={handleAddClusterServiceClick}
        disabled={isAddingServices || !cluster}
        iconLeft={isAddingServices ? 'g1-load' : undefined}
      >
        Add service
      </Button>
    </TableToolbar>
  );
};

export default ClustersTableHeader;
