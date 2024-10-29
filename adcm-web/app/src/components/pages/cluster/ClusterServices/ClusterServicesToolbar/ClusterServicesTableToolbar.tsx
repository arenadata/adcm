import { Button } from '@uikit';
import ClusterServicesFilters from './ClusterServicesTableFilters';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import { useDispatch, useStore } from '@hooks';
import { openCreateDialog } from '@store/adcm/cluster/services/servicesActionsSlice';

const ClustersTableHeader = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const isAddingServices = useStore(({ adcm }) => adcm.servicesActions.isActionInProgress);

  const handleAddClusterServiceClick = () => {
    dispatch(openCreateDialog());
  };

  return (
    <TableToolbar>
      <ClusterServicesFilters />
      <Button
        onClick={handleAddClusterServiceClick}
        disabled={isAddingServices || !cluster}
        iconLeft={isAddingServices ? { name: 'g1-load', className: 'spin' } : undefined}
      >
        Add services
      </Button>
    </TableToolbar>
  );
};

export default ClustersTableHeader;
