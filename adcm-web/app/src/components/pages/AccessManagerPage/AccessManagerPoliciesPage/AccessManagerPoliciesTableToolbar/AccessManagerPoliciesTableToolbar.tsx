import React from 'react';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import { Button } from '@uikit';
import AccessManagerPoliciesTableFilters from './AccessManagerPoliciesTableFilters';

const AccessManagerPoliciesTableToolbar: React.FC = () => {
  return (
    <TableToolbar>
      <AccessManagerPoliciesTableFilters />
      <Button>Create Policy</Button>
    </TableToolbar>
  );
};

export default AccessManagerPoliciesTableToolbar;
