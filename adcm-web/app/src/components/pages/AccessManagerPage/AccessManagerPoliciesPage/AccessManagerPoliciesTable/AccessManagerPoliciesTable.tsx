import type React from 'react';
import { useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { Button, ExpandableRowComponent, IconButton, Table, TableCell, EllipsedTextTableCell } from '@uikit';
import { columns } from './AccessManagerPoliciesTable.constants';
import { orElseGet } from '@utils/checkUtils';
import { openDeleteDialog, openUpdateDialog } from '@store/adcm/policies/policiesActionsSlice';
import { setSortParams } from '@store/adcm/policies/policiesTableSlice';
import type { SortParams } from '@uikit/types/list.types';
import type { AdcmPolicy } from '@models/adcm';
import AccessManagerPoliciesTableExpandedContent from './AccessManagerPoliciesTableExpandedContent/AccessManagerPoliciesTableExpandedContent';
import { isShowSpinner } from '@uikit/Table/Table.utils';

const AccessManagerPoliciesTable: React.FC = () => {
  const dispatch = useDispatch();

  const policies = useStore(({ adcm }) => adcm.policies.policies);
  const isLoading = useStore(
    ({ adcm }) => adcm.policiesActions.isActionInProgress || isShowSpinner(adcm.policies.loadState),
  );
  const sortParams = useStore(({ adcm }) => adcm.policiesTable.sortParams);

  const handleEditClick = (policy: AdcmPolicy) => () => {
    dispatch(openUpdateDialog(policy));
  };

  const handleDeleteClick = (policy: AdcmPolicy) => () => {
    dispatch(openDeleteDialog(policy));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});

  const handleExpandClick = (id: number) => {
    setExpandableRows({
      ...expandableRows,
      [id]: expandableRows[id] === undefined ? true : !expandableRows[id],
    });
  };

  return (
    <Table
      variant="secondary"
      columns={columns}
      isLoading={isLoading}
      sortParams={sortParams}
      onSorting={handleSorting}
    >
      {policies.map((policy) => {
        return (
          <ExpandableRowComponent
            key={policy.id}
            colSpan={columns.length}
            isExpanded={expandableRows[policy.id] || false}
            expandedContent={<AccessManagerPoliciesTableExpandedContent objects={policy.objects} />}
          >
            <TableCell>{policy.name}</TableCell>
            <TableCell>{orElseGet(policy.description)}</TableCell>
            <TableCell>{orElseGet(policy.role?.displayName)}</TableCell>
            <EllipsedTextTableCell
              minWidth="300px"
              value={policy.groups.map((group) => group.displayName).join(', ')}
            />
            <EllipsedTextTableCell
              minWidth="300px"
              value={policy.objects.map((object) => object.displayName).join(', ')}
            />
            <TableCell>
              <Button
                className={expandableRows[policy.id] ? 'is-active' : ''}
                variant="secondary"
                iconLeft="dots"
                onClick={() => handleExpandClick(policy.id)}
                disabled={!policy.objects.length}
                placeholder="Expand"
              />
            </TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-edit" size={32} onClick={handleEditClick(policy)} title="Edit" />
              <IconButton icon="g1-delete" size={32} onClick={handleDeleteClick(policy)} title="Delete" />
            </TableCell>
          </ExpandableRowComponent>
        );
      })}
    </Table>
  );
};

export default AccessManagerPoliciesTable;
