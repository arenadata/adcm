import { useDispatch } from '@hooks';
import ClustersTableFilters from './ClustersTableFilters';
import { Button } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import { open as openCreateClusterDialog } from '@store/adcm/clusters/dialogs/createClusterDialogSlice';

const ClustersTableHeader = () => {
  const dispatch = useDispatch();

  const handleCreateClusterClick = () => {
    dispatch(openCreateClusterDialog());
  };

  return (
    <TableToolbar>
      <ClustersTableFilters />
      <Button onClick={handleCreateClusterClick}>Create cluster</Button>
    </TableToolbar>
  );
};

export default ClustersTableHeader;
