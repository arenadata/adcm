import CreateClusterDialog from './CreateClusterDialog/CreateClusterDialog';
import UpgradeClusterDialog from './UpgradeClusterDialog/UpgradeClusterDialog';
import DeleteClusterDialog from './DeleteClusterDialog/DeleteClusterDialog';
import ClusterDynamicActionDialog from './ClusterDynamicActionDialog/ClusterDynamicActionDialog';

const ClusterDialogs = () => {
  return (
    <>
      <CreateClusterDialog />
      <UpgradeClusterDialog />
      <DeleteClusterDialog />
      <ClusterDynamicActionDialog />
    </>
  );
};

export default ClusterDialogs;
