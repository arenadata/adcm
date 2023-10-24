import React from 'react';
import HostDeleteDialog from './HostDeleteDialog/HostDeleteDialog';
import CreateHostDialog from './CreateHostDialog/CreateHostDialog';
import LinkHostDialog from './LinkHostDialog/LinkHostDialog';
import UnlinkHostDialog from './UnlinkHostDialog/UnlinkHostDialog';
import MaintenanceModeDialog from './HostMaintenanceModeDialog/HostMaintenanceModeDialog';
import HostDynamicActionDialog from './HostDynamicActionDialog/HostDynamicActionDialog';
import RenameHostDialog from './UpdateHostDialog/UpdateHostDialog';

const HostsActionsDialogs: React.FC = () => {
  return (
    <>
      <HostDeleteDialog />
      <CreateHostDialog />
      <LinkHostDialog />
      <UnlinkHostDialog />
      <MaintenanceModeDialog />
      <HostDynamicActionDialog />
      <RenameHostDialog />
    </>
  );
};

export default HostsActionsDialogs;
