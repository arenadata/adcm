import { Button } from '@uikit';
import ClusterServicesFilters from './ClusterServicesTableFilters';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';

const ClustersTableHeader = () => {
  const handleCreateClusterClick = () => {
    console.info('Create service dialog');
  };

  return (
    <TableToolbar>
      <ClusterServicesFilters />
      <Button onClick={handleCreateClusterClick}>Add service</Button>
    </TableToolbar>
  );
};

export default ClustersTableHeader;
