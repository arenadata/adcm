import React from 'react';
import HostComponentsTable from './HostComponentsTable/HostComponentsTable';
import HostComponentsTableToolbar from './HostComponentsTableToolbar/HostComponentsTableToolbar';
import HostComponentsTableFooter from './HostComponentsTableFooter/HostComponentsTableFooter';

const HostComponents: React.FC = () => {
  return (
    <>
      <HostComponentsTableToolbar />
      <HostComponentsTable />
      <HostComponentsTableFooter />
    </>
  );
};

export default HostComponents;
