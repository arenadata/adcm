import ClustersTableToolbar from './ClustersTableToolbar/ClustersTableToolbar';
import ClustersTable from './ClustersTable/ClustersTable';
import ClustersTableFooter from './ClustersTableFooter/ClustersTableFooter';
import Dialogs from './Dialogs';
import { useRequestClusters } from './useRequestClusters';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';

const ClusterPage = () => {
  useRequestClusters();
  return (
    <TableContainer variant="easy">
      <ClustersTableToolbar />
      <ClustersTable />
      <ClustersTableFooter />
      <Dialogs />
    </TableContainer>
  );
};

export default ClusterPage;
