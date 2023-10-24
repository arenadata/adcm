import React from 'react';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import { useRequestBundles } from './useRequestBundles';
import BundlesTable from './BundlesTable/BundlesTable';
import BundlesTableFooter from './BundlesTableFooter/BundlesTableFooter';
import BundlesTableToolbar from './BundlesTableToolbar/BundlesTableToolbar';
import BundlesActionsDialogs from './BundlesActionsDialogs/BundlesActionsDialogs';

const BundlesPage: React.FC = () => {
  useRequestBundles();

  return (
    <TableContainer variant="easy">
      <BundlesTableToolbar />
      <BundlesTable />
      <BundlesTableFooter />
      <BundlesActionsDialogs />
    </TableContainer>
  );
};

export default BundlesPage;
