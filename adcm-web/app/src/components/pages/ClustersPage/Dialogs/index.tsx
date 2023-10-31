import CreateClusterDialog from './CreateClusterDialog/CreateClusterDialog';
import UpgradeClusterDialog from './UpgradeClusterDialog/UpgradeClusterDialog';
import DeleteClusterDialog from './DeleteClusterDialog/DeleteClusterDialog';
import ClusterDynamicActionDialog from './ClusterDynamicActionDialog/ClusterDynamicActionDialog';
import UpdateClusterDialog from './UpdateClusterDialog/UpdateClusterDialog';

const ClusterDialogs = () => {
  return (
    <>
      <CreateClusterDialog />
      <UpgradeClusterDialog />
      <DeleteClusterDialog />
      <ClusterDynamicActionDialog />
      <UpdateClusterDialog />
    </>
  );
};

export default ClusterDialogs;
