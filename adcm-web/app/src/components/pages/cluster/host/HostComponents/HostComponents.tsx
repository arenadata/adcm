import React from 'react';
import HostComponentsTable from '@commonComponents/host/HostComponentsTable/HostComponentsTable';
import HostComponentsTableToolbar from './HostComponentsTableToolbar/HostComponentsTableToolbar';
import HostComponentsTableFooter from './HostComponentsTableFooter/HostComponentsTableFooter';
import { useRequestHostComponents } from './useRequestHostComponents';
import HostComponentsDynamicActionDialog from './HostComponentsDynamicActionDialog/HostComponentsDynamicActionDialog';

const HostComponents: React.FC = () => {
  useRequestHostComponents();
  return (
    <>
      <HostComponentsTableToolbar />
      <HostComponentsTable />
      <HostComponentsTableFooter />
      <HostComponentsDynamicActionDialog />
    </>
  );
};

export default HostComponents;
