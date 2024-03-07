import { Dispatch, SetStateAction, useCallback } from 'react';
import { Table, TableRow, TableCell, IconButton, Checkbox } from '@uikit';
import { useDispatch, useStore, useSelectedItems } from '@hooks';
import { columns } from './AccessManagerUsersTable.constants';
import {
  openBlockDialog,
  openDeleteDialog,
  openUnblockDialog,
  openUserUpdateDialog,
  setSelectedItemsIds as setSelectedUsersIds,
} from '@store/adcm/users/usersActionsSlice';
import { setSortParams } from '@store/adcm/users/usersTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { AdcmUser, AdcmUserStatus } from '@models/adcm';
import { isShowSpinner } from '@uikit/Table/Table.utils';
import UserStatusCell from '@commonComponents/Table/Cells/LabelIconCell/UserStatusCell';

const AccessManagerUsersTable = () => {
  const dispatch = useDispatch();
  const users = useStore((s) => s.adcm.users.users);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.users.loadState));
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

  const handleBlockClick = (id: number) => () => {
    dispatch(openBlockDialog([id]));
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
            <UserStatusCell user={user} />
            <TableCell>{user.email}</TableCell>
            <TableCell isMultilineText>{userGroupsNames}</TableCell>
            <TableCell>{user.type}</TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-edit" size={32} title="Edit" onClick={handleEditUserClick(user)} />
              {user.status === AdcmUserStatus.Blocked && (
                <IconButton icon="g1-unblock" size={32} title="Unblock" onClick={handleUnblockClick(user.id)} />
              )}
              {user.status === AdcmUserStatus.Active && (
                <IconButton icon="g1-block" size={32} title="Block" onClick={handleBlockClick(user.id)} />
              )}
              <IconButton icon="g1-delete" size={32} onClick={handleDeleteClick(user.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default AccessManagerUsersTable;
