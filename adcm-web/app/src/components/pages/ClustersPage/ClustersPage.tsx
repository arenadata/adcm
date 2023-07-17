import ClustersTableToolbar from './ClustersTableToolbar/ClustersTableToolbar';
import ClustersTable from './ClustersTable/ClustersTable';
import ClustersTableFooter from './ClustersTableFooter/ClustersTableFooter';
import Dialogs from './Dialogs';
import { useRequestClusters } from './useRequestClusters';

const ClusterPage = () => {
  useRequestClusters();
  return (
    <>
      <ClustersTableToolbar />
      <ClustersTable />
      <ClustersTableFooter />
      <Dialogs />
    </>
  );
};

export default ClusterPage;
