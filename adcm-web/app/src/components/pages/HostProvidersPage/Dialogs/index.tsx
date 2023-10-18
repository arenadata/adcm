import CreateHostProviderDialog from './CreateHostProviderDialog/CreateHostProviderDialog';
import HostProviderDynamicActionDialog from './HostProviderDynamicActionDialog/HostProviderDynamicActionDialog';
import HostProviderUpgradeDialog from './HostProviderUpgradeDialog/HostProviderUpgradeDialog';
import HostProvidersDeleteDialog from '@pages/HostProvidersPage/Dialogs/HostProvidersDeleteDialog/HostProvidersDeleteDialog';

const HostProviderDialogs = () => {
  return (
    <>
      <CreateHostProviderDialog />
      <HostProvidersDeleteDialog />
      <HostProviderDynamicActionDialog />
      <HostProviderUpgradeDialog />
    </>
  );
};

export default HostProviderDialogs;
