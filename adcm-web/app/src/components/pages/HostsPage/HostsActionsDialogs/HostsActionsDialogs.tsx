import type React from 'react';
import HostDeleteDialog from './HostDeleteDialog/HostDeleteDialog';
import CreateHostDialog from './CreateHostDialog/CreateHostDialog';
import LinkHostDialog from './LinkHostDialog/LinkHostDialog';
import UnlinkHostDialog from './UnlinkHostDialog/UnlinkHostDialog';
import MaintenanceModeDialog from './HostMaintenanceModeDialog/HostMaintenanceModeDialog';
import HostDynamicActionDialog from './HostDynamicActionDialog/HostDynamicActionDialog';
import RenameHostDialog from './UpdateHostDialog/UpdateHostDialog';
import HostShareDialog from './HostShareDialog/HostShareDialog';
import ShareHostDialog from './ShareHostDialog/ShareHostDialog';

const HostsActionsDialogs: React.FC = () => {
  return (
    <>
      <HostDeleteDialog />
      <CreateHostDialog />
      <LinkHostDialog />
      <UnlinkHostDialog />
      <ShareHostDialog />
      <MaintenanceModeDialog />
      <HostDynamicActionDialog />
      <RenameHostDialog />
      <HostShareDialog />
    </>
  );
};

export default HostsActionsDialogs;
