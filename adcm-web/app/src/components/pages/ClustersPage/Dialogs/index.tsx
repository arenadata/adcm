import CreateClusterDialog from './CreateClusterDialog/CreateClusterDialog';
import UpgradeClusterDialog from './UpgradeClusterDialog/UpgradeClusterDialog';
import DeleteClusterDialog from './DeleteClusterDialog/DeleteClusterDialog';
import ClusterDynamicActionDialog from './ClusterDynamicActionDialog/ClusterDynamicActionDialog';
import RenameClusterDialog from './RenameClusterDialog/RenameClusterDialog';

const ClusterDialogs = () => {
  return (
    <>
      <CreateClusterDialog />
      <UpgradeClusterDialog />
      <DeleteClusterDialog />
      <ClusterDynamicActionDialog />
      <RenameClusterDialog />
    </>
  );
};

export default ClusterDialogs;
