import type React from 'react';
import HostComponentsTableFilters from './HostComponentsTableFilter';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';

const HostComponentsTableToolbar: React.FC = () => {
  return (
    <>
      <TableToolbar>
        <HostComponentsTableFilters />
      </TableToolbar>
    </>
  );
};

export default HostComponentsTableToolbar;
