import type React from 'react';
import AccessManagerPoliciesTable from './AccessManagerPoliciesTable/AccessManagerPoliciesTable';
import { useRequestAccessManagerPolicies } from './useRequestAccessManagerPolicies';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import AccessManagerPoliciesTableToolbar from './AccessManagerPoliciesTableToolbar/AccessManagerPoliciesTableToolbar';
import AccessManagerPoliciesTableFooter from './AccessManagerPoliciesTableFooter/AccessManagerPoliciesTableFooter';
import AccessManagerPoliciesDialogs from './Dialogs';

const AccessManagerPoliciesPage: React.FC = () => {
  useRequestAccessManagerPolicies();
  return (
    <TableContainer variant="easy">
      <AccessManagerPoliciesTableToolbar />
      <AccessManagerPoliciesTable />
      <AccessManagerPoliciesTableFooter />
      <AccessManagerPoliciesDialogs />
    </TableContainer>
  );
};

export default AccessManagerPoliciesPage;
