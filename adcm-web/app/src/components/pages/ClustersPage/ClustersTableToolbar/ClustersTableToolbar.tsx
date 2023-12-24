import { useDispatch } from '@hooks';
import ClustersTableFilters from './ClustersTableFilters';
import { Button } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import { openClusterCreateDialog } from '@store/adcm/clusters/clustersActionsSlice';

const ClustersTableHeader = () => {
  const dispatch = useDispatch();

  const handleCreateClusterClick = () => {
    dispatch(openClusterCreateDialog());
  };

  return (
    <TableToolbar>
      <ClustersTableFilters />
      <Button onClick={handleCreateClusterClick}>Create cluster</Button>
    </TableToolbar>
  );
};

export default ClustersTableHeader;
