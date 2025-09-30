import CreateClusterDialog from './CreateClusterDialog/CreateClusterDialog';
import UpgradeClusterDialog from './UpgradeClusterDialog/UpgradeClusterDialog';
import DeleteClusterDialog from './DeleteClusterDialog/DeleteClusterDialog';
import ClusterDynamicActionDialog from './ClusterDynamicActionDialog/ClusterDynamicActionDialog';
import UpdateClusterDialog from './UpdateClusterDialog/UpdateClusterDialog';
import EditClusterDescriptionDialog from './EditClusterDescriptionDialog/EditClusterDescriptionDialog';
import ClusterActionWizardDialog from './ClusterDynamicActionWizardDialog/ClusterDynamicActionWizardDialog';

const ClusterDialogs = () => {
  return (
    <>
      <CreateClusterDialog />
      <UpgradeClusterDialog />
      <DeleteClusterDialog />
      <ClusterDynamicActionDialog />
      <UpdateClusterDialog />
      <EditClusterDescriptionDialog />
      <ClusterActionWizardDialog />
    </>
  );
};

export default ClusterDialogs;
