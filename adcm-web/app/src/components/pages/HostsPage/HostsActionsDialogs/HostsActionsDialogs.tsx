import React from 'react';
import HostDeleteDialog from './HostDeleteDialog/HostDeleteDialog';
import CreateHostDialog from './CreateHostDialog/CreateHostDialog';
import LinkHostDialog from './LinkHostDialog/LinkHostDialog';
import UnlinkHostDialog from './UnlinkHostDialog/UnlinkHostDialog';
import MaintenanceModeDialog from './MaintenanceModeDialog/MaintenanceModeDialog';

const HostsActionsDialogs: React.FC = () => {
  return (
    <>
      <HostDeleteDialog />
      <CreateHostDialog />
      <LinkHostDialog />
      <UnlinkHostDialog />
      <MaintenanceModeDialog />
    </>
  );
};

export default HostsActionsDialogs;
