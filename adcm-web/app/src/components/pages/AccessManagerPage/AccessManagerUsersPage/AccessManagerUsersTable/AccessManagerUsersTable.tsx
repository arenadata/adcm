import { Dispatch, SetStateAction, useCallback } from 'react';
import { Table, TableRow, TableCell, IconButton, Checkbox } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './AccessManagerUsersTable.constants';
import {
  openUnblockDialog,
  openUserUpdateDialog,
  setSelectedItemsIds as setSelectedUsersIds,
} from '@store/adcm/users/usersActionsSlice';
import { setSortParams } from '@store/adcm/users/usersTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { AdcmUser, AdcmUserStatus } from '@models/adcm';
import { useSelectedItems } from '@uikit/hooks/useSelectedItems';
import { openDeleteDialog } from '@store/adcm/users/usersActionsSlice';

const AccessManagerUsersTable = () => {
  const dispatch = useDispatch();
  const users = useStore((s) => s.adcm.users.users);
  const isLoading = useStore((s) => s.adcm.users.isLoading);
  const sortParams = useStore((s) => s.adcm.usersTable.sortParams);
  const selectedItemsIds = useStore(({ adcm }) => adcm.usersActions.selectedItemsIds);

  const setSelectedItemsIds = useCallback<Dispatch<SetStateAction<number[]>>>(
    (arg) => {
      const value = typeof arg === 'function' ? arg(selectedItemsIds) : arg;
      dispatch(setSelectedUsersIds(value));
    },
    [dispatch, selectedItemsIds],
  );

  const getUniqKey = ({ id }: AdcmUser) => id;
  const { isAllItemsSelected, toggleSelectedAllItems, getHandlerSelectedItem, isItemSelected } = useSelectedItems(
    users,
    getUniqKey,
    selectedItemsIds,
    setSelectedItemsIds,
  );

  const handleDeleteClick = (id: number) => () => {
    dispatch(openDeleteDialog(id));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const handleUnblockClick = (id: number) => () => {
    dispatch(openUnblockDialog([id]));
  };

  const handleEditUserClick = (user: AdcmUser) => () => {
    dispatch(openUserUpdateDialog(user));
  };

  return (
    <Table
      isLoading={isLoading}
      columns={columns}
      sortParams={sortParams}
      onSorting={handleSorting}
      isAllSelected={isAllItemsSelected}
      toggleSelectedAll={toggleSelectedAllItems}
      variant="tertiary"
    >
      {users.map((user) => {
        const userGroupsNames = user.groups.map((group) => group.displayName).join(', ');

        return (
          <TableRow key={user.id}>
            <TableCell>
              <Checkbox checked={isItemSelected(user)} onChange={getHandlerSelectedItem(user)} />
            </TableCell>
            <TableCell>{user.username}</TableCell>
            <TableCell>{user.status}</TableCell>
            <TableCell>{user.email}</TableCell>
            <TableCell>{userGroupsNames}</TableCell>
            <TableCell>{user.type}</TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-edit" size={32} title="Edit" onClick={handleEditUserClick(user)} />
              <IconButton
                disabled={user.status !== AdcmUserStatus.Blocked}
                icon="g1-unblock"
                size={32}
                title="Unblock"
                onClick={handleUnblockClick(user.id)}
              />
              <IconButton icon="g1-delete" size={32} onClick={handleDeleteClick(user.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default AccessManagerUsersTable;
