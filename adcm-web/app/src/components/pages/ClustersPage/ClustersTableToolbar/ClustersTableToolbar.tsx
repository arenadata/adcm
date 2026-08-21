import { useDispatch } from '@hooks';
import ClustersTableFilters from './ClustersTableFilters';
import { Button } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import { openCreateDialog } from '@store/adcm/clusters/clustersActionsSlice';

const ClustersTableToolbar = () => {
  const dispatch = useDispatch();

  const handleCreateClusterClick = () => {
    dispatch(openCreateDialog());
  };

  return (
    <TableToolbar>
      <ClustersTableFilters />
      <Button onClick={handleCreateClusterClick}>Create cluster</Button>
    </TableToolbar>
  );
};

export default ClustersTableToolbar;
