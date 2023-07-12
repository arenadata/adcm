import ClustersTableFilters from './ClustersTableFilters';
import { Button } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';

const ClustersTableHeader = () => (
  <TableToolbar>
    <ClustersTableFilters />
    <Button>Create cluster</Button>
  </TableToolbar>
);

export default ClustersTableHeader;
