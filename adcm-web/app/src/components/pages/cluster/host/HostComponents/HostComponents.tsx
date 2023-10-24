import React from 'react';
import HostComponentsTable from '@commonComponents/host/HostComponentsTable/HostComponentsTable';
import HostComponentsTableToolbar from './HostComponentsTableToolbar/HostComponentsTableToolbar';
import HostComponentsTableFooter from './HostComponentsTableFooter/HostComponentsTableFooter';
import ServiceComponentsDynamicActionDialog from '@pages/cluster/service/ServiceComponents/Dialogs/ServiceComponentsDynamicActionDialog/ServiceComponentsDynamicActionDialog';
import { useRequestHostComponents } from '../useRequestHostComponents';

const HostComponents: React.FC = () => {
  useRequestHostComponents();
  return (
    <>
      <HostComponentsTableToolbar />
      <HostComponentsTable />
      <HostComponentsTableFooter />
      <ServiceComponentsDynamicActionDialog />
    </>
  );
};

export default HostComponents;
