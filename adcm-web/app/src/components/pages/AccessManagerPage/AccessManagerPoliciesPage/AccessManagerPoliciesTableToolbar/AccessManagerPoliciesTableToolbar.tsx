import type React from 'react';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import { Button } from '@uikit';
import AccessManagerPoliciesTableFilters from './AccessManagerPoliciesTableFilters';
import { useDispatch, useStore } from '@hooks';
import { openCreateDialog } from '@store/adcm/policies/policiesActionsSlice';

const AccessManagerPoliciesTableToolbar: React.FC = () => {
  const dispatch = useDispatch();
  const isCreating = useStore(({ adcm }) => adcm.policiesActions.isActionInProgress);

  const handleAddPolicyClick = () => {
    dispatch(openCreateDialog());
  };

  return (
    <TableToolbar>
      <AccessManagerPoliciesTableFilters />
      <Button
        onClick={handleAddPolicyClick}
        disabled={isCreating}
        iconLeft={isCreating ? { name: 'g1-load', className: 'spin' } : undefined}
      >
        Create policy
      </Button>
    </TableToolbar>
  );
};

export default AccessManagerPoliciesTableToolbar;
