import CreateClusterDialog from './CreateClusterDialog/CreateClusterDialog';
import UpgradeClusterDialog from './UpgradeClusterDialog/UpgradeClusterDialog';
import DeleteClusterDialog from './DeleteClusterDialog/DeleteClusterDialog';

const ClusterDialogs = () => {
  return (
    <>
      <CreateClusterDialog />
      <UpgradeClusterDialog />
      <DeleteClusterDialog />
    </>
  );
};

export default ClusterDialogs;
