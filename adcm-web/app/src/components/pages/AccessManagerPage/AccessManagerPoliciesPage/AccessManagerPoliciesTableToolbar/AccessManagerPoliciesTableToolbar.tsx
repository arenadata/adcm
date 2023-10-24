import React from 'react';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import { Button } from '@uikit';
import AccessManagerPoliciesTableFilters from './AccessManagerPoliciesTableFilters';
import { useDispatch, useStore } from '@hooks';
import { openPoliciesAddDialog } from '@store/adcm/policies/policiesActionsSlice';

const AccessManagerPoliciesTableToolbar: React.FC = () => {
  const dispatch = useDispatch();
  const isCreating = useStore(({ adcm }) => adcm.policiesActions.isCreating);

  const handleAddPolicyClick = () => {
    dispatch(openPoliciesAddDialog());
  };

  return (
    <TableToolbar>
      <AccessManagerPoliciesTableFilters />
      <Button onClick={handleAddPolicyClick} disabled={isCreating} iconLeft={isCreating ? 'g1-load' : undefined}>
        Create Policy
      </Button>
    </TableToolbar>
  );
};

export default AccessManagerPoliciesTableToolbar;
