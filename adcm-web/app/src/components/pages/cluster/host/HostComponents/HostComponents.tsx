import React from 'react';
import HostComponentsTable from './HostComponentsTable/HostComponentsTable';
import HostComponentsTableToolbar from './HostComponentsTableToolbar/HostComponentsTableToolbar';
import HostComponentsTableFooter from './HostComponentsTableFooter/HostComponentsTableFooter';
import { useRequestHostComponents } from './useRequestHostComponents';
import HostComponentsDynamicActionDialog from './HostComponentsDynamicActionDialog/HostComponentsDynamicActionDialog';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';

const HostComponents: React.FC = () => {
  const { accessCheckStatus } = useRequestHostComponents();

  return (
    <PermissionsChecker requestState={accessCheckStatus}>
      <HostComponentsTableToolbar />
      <HostComponentsTable />
      <HostComponentsTableFooter />
      <HostComponentsDynamicActionDialog />
    </PermissionsChecker>
  );
};

export default HostComponents;
