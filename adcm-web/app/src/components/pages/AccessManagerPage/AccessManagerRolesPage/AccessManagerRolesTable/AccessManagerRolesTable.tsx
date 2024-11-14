import { Table, TableCell, IconButton, Button, ExpandableRowComponent, EllipsedTextTableCell } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './AccessManagerRolesTable.constants';
import { setSortParams } from '@store/adcm/roles/rolesTableSlice';
import type { SortParams } from '@uikit/types/list.types';
import { openDeleteDialog, openUpdateDialog } from '@store/adcm/roles/rolesActionsSlice';
import { useState } from 'react';
import AccessManagerRolesTableExpandedContent from './AccessManagerRolesTableExpandedContent/AccessManagerRolesTableExpandedContent';
import s from './AccessManagerRolesTable.module.scss';
import type { AdcmRole } from '@models/adcm';
import { isShowSpinner } from '@uikit/Table/Table.utils';
import { orElseGet } from '@utils/checkUtils';

const AccessManagerRolesTable = () => {
  const dispatch = useDispatch();

  const roles = useStore((s) => s.adcm.roles.roles);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.roles.loadState));
  const sortParams = useStore((s) => s.adcm.rolesTable.sortParams);

  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});

  const handleExpandClick = (id: number) => {
    setExpandableRows({
      ...expandableRows,
      [id]: expandableRows[id] === undefined ? true : !expandableRows[id],
    });
  };

  const handleDeleteClick = (role: AdcmRole) => () => {
    dispatch(openDeleteDialog(role));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const getHandleOpenUpdateDialog = (role: AdcmRole) => () => {
    dispatch(openUpdateDialog(role));
  };

  return (
    <Table
      isLoading={isLoading}
      columns={columns}
      sortParams={sortParams}
      onSorting={handleSorting}
      variant="secondary"
      className={s.tableRoles}
    >
      {roles.map((role) => {
        return (
          <ExpandableRowComponent
            key={role.id}
            colSpan={columns.length}
            isExpanded={expandableRows[role.id] || false}
            isInactive={!role.children?.length}
            expandedContent={<AccessManagerRolesTableExpandedContent children={role.children || []} />}
          >
            <TableCell className={s.roleName}>{role.displayName}</TableCell>
            <TableCell>{role.description}</TableCell>
            <EllipsedTextTableCell
              minWidth="600px"
              value={orElseGet(role.children?.map((child) => child.displayName).join(', '))}
            />
            <TableCell>
              <Button
                className={expandableRows[role.id] ? 'is-active' : ''}
                variant="secondary"
                iconLeft="dots"
                onClick={() => handleExpandClick(role.id)}
                disabled={!role.children?.length}
                placeholder="Expand"
              />
            </TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton
                icon="g1-edit"
                size={32}
                title="Edit"
                disabled={role.isBuiltIn}
                onClick={getHandleOpenUpdateDialog(role)}
              />
              <IconButton
                icon="g1-delete"
                size={32}
                onClick={handleDeleteClick(role)}
                title="Delete"
                disabled={role.isBuiltIn}
              />
            </TableCell>
          </ExpandableRowComponent>
        );
      })}
    </Table>
  );
};

export default AccessManagerRolesTable;
