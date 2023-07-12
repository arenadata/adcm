import ClustersTableToolbar from './ClustersTableToolbar/ClustersTableToolbar';
import ClustersTable from './ClustersTable/ClustersTable';
import ClustersTableFooter from './ClustersTableFooter/ClustersTableFooter';
import { useRequestClusters } from './useRequestClusters';

const ClusterPage = () => {
  useRequestClusters();

  return (
    <>
      <ClustersTableToolbar />
      <ClustersTable />
      <ClustersTableFooter />
    </>
  );
};

export default ClusterPage;
