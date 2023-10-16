import CreateHostProviderDialog from './CreateHostProviderDialog/CreateHostProviderDialog';
import HostProviderDynamicActionDialog from './HostProviderDynamicActionDialog/HostProviderDynamicActionDialog';
import HostProviderUpgradeDialog from './HostProviderUpgradeDialog/HostProviderUpgradeDialog';

const HostProviderDialogs = () => {
  return (
    <>
      <CreateHostProviderDialog />
      <HostProviderDynamicActionDialog />
      <HostProviderUpgradeDialog />
    </>
  );
};

export default HostProviderDialogs;
