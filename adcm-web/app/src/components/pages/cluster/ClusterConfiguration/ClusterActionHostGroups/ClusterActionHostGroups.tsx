import { useRequestClusterActionHostGroups } from './useRequestClusterActionHostGroups';
import ClusterActionHostGroupsTable from './ClusterActionHostGroupsTable/ClusterActionHostGroupsTable';

const ClusterActionHostGroups = () => {
  useRequestClusterActionHostGroups();

  return (
    <>
      <ClusterActionHostGroupsTable />
    </>
  );
};

export default ClusterActionHostGroups;
