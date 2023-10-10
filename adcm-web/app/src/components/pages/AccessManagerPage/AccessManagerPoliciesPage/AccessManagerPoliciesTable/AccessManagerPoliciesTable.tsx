import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { IconButton, Table, TableCell, TableRow } from '@uikit';
import { columns } from './AccessManagerPoliciesTable.constants';
import { orElseGet } from '@utils/checkUtils';
import { openDeleteDialog, openPoliciesEditDialog } from '@store/adcm/policies/policiesActionsSlice';
import { setSortParams } from '@store/adcm/policies/policiesTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { AdcmPolicy } from '@models/adcm';

const AccessManagerPoliciesTable: React.FC = () => {
  const dispatch = useDispatch();

  const policies = useStore(({ adcm }) => adcm.policies.policies);
  const isLoading = useStore(({ adcm }) => adcm.policies.isLoading);
  const sortParams = useStore(({ adcm }) => adcm.policiesTable.sortParams);

  const handleEditClick = (policy: AdcmPolicy) => () => {
    dispatch(openPoliciesEditDialog(policy));
  };

  const handleDeleteClick = (policyId: number) => () => {
    dispatch(openDeleteDialog(policyId));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table variant="primary" columns={columns} isLoading={isLoading} sortParams={sortParams} onSorting={handleSorting}>
      {policies.map((policy) => {
        return (
          <TableRow key={policy.id}>
            <TableCell>{policy.name}</TableCell>
            <TableCell>{orElseGet(policy.description)}</TableCell>
            <TableCell>{policy.role.displayName}</TableCell>
            <TableCell>{policy.groups.map((group) => group.displayName).join(', ')}</TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-edit" size={32} onClick={handleEditClick(policy)} title="Edit" />
              <IconButton icon="g1-delete" size={32} onClick={handleDeleteClick(policy.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default AccessManagerPoliciesTable;
