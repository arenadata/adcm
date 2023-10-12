import React from 'react';
import HostComponentsTableToolbar from './HostComponentsTableToolbar/HostComponentsTableToolbar';
import HostComponentsTableFooter from './HostComponentsTableFooter/HostComponentsTableFooter';
import HostComponentsTable from './HostComponentsTable/HostComponentsTable';

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
