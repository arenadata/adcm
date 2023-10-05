import { Link, generatePath } from 'react-router-dom';
import { Table, TableCell, IconButton, Button, ExpandableRowComponent } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './AccessManagerRolesTable.constants';
import { setSortParams } from '@store/adcm/roles/rolesTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { ACCESS_MANAGER_PAGE_URLS } from '@pages/AccessManagerPage/AccessManagerPage.constants';
import { openDeleteDialog, openUpdateDialog } from '@store/adcm/roles/rolesActionsSlice';
import { useState } from 'react';
import AccessManagerRolesTableExpandedContent from './AccessManagerRolesTableExpandedContent/AccessManagerRolesTableExpandedContent';
import s from './AccessManagerRolesTable.module.scss';
import cn from 'classnames';
import { AdcmRole } from '@models/adcm';

const AccessManagerRolesTable = () => {
  const dispatch = useDispatch();

  const roles = useStore((s) => s.adcm.roles.roles);
  const isLoading = useStore((s) => s.adcm.roles.isLoading);
  const sortParams = useStore((s) => s.adcm.rolesTable.sortParams);

  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});

  const handleExpandClick = (id: number) => {
    setExpandableRows({
      ...expandableRows,
      [id]: expandableRows[id] === undefined ? true : !expandableRows[id],
    });
  };

  const handleDeleteClick = (id: number) => () => {
    dispatch(openDeleteDialog(id));
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
      className={s.rolesTable}
      variant="secondary"
    >
      {roles.map((role) => {
        return (
          <ExpandableRowComponent
            key={role.id}
            colSpan={columns.length}
            isExpanded={expandableRows[role.id] || false}
            isInactive={!role.children?.length}
            expandedContent={<AccessManagerRolesTableExpandedContent children={role.children || []} />}
            className={cn(s.rolesTable__roleRow, { [s.expandedRow]: expandableRows[role.id] })}
            expandedClassName={s.rolesTable__expandedRoleRow}
          >
            <TableCell className={s.rolesTable__roleRow__roleName}>
              <Link to={generatePath(ACCESS_MANAGER_PAGE_URLS.Role, { roleId: role.id + '' })}>{role.displayName}</Link>
            </TableCell>
            <TableCell>{role.description}</TableCell>
            <TableCell>{role.children?.map((child) => child.displayName).join(', ')}</TableCell>
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
                onClick={handleDeleteClick(role.id)}
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
