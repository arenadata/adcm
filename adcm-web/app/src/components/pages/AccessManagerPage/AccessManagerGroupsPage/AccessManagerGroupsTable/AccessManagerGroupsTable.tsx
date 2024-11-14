import type { Dispatch, SetStateAction } from 'react';
import { useCallback } from 'react';
import { Table, TableRow, TableCell, IconButton, Checkbox } from '@uikit';
import { useDispatch, useStore, useSelectedItems } from '@hooks';
import { columns } from './AccessManagerGroupsTable.constants';
import {
  openUpdateDialog,
  openDeleteDialog,
  setSelectedGroupsIds as setSelectedGroupsIdsFromStore,
} from '@store/adcm/groups/groupsActionsSlice';
import { setSortParams } from '@store/adcm/groups/groupsTableSlice';
import type { SortParams } from '@uikit/types/list.types';
import type { AdcmGroup } from '@models/adcm';
import { isShowSpinner } from '@uikit/Table/Table.utils';

const AccessManagerGroupsTable = () => {
  const dispatch = useDispatch();
  const groups = useStore((s) => s.adcm.groups.groups);
  const selectedGroupIds = useStore((s) => s.adcm.groupsActions.selectedGroupsIds);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.groups.loadState));
  const sortParams = useStore((s) => s.adcm.groupsTable.sortParams);

  const setSelectedGroups = useCallback<Dispatch<SetStateAction<number[]>>>(
    (arg) => {
      const value = typeof arg === 'function' ? arg(selectedGroupIds) : arg;
      dispatch(setSelectedGroupsIdsFromStore(value));
    },
    [dispatch, selectedGroupIds],
  );

  const getUniqKey = ({ id }: AdcmGroup) => id;
  const { isAllItemsSelected, toggleSelectedAllItems, getHandlerSelectedItem, isItemSelected } = useSelectedItems(
    groups,
    getUniqKey,
    selectedGroupIds,
    setSelectedGroups,
  );

  const getHandleDeleteClick = (group: AdcmGroup) => () => {
    dispatch(openDeleteDialog(group));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const getHandleOpenUpdateDialog = (group: AdcmGroup) => () => {
    dispatch(openUpdateDialog(group));
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
      {groups.map((group) => {
        return (
          <TableRow key={group.id}>
            <TableCell>
              <Checkbox checked={isItemSelected(group)} onChange={getHandlerSelectedItem(group)} />
            </TableCell>
            <TableCell>{group.displayName}</TableCell>
            <TableCell>{group.description}</TableCell>
            <TableCell>{group.users.map((user) => user.username).join(', ')}</TableCell>
            <TableCell>{group.type}</TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-edit" size={32} title="Edit" onClick={getHandleOpenUpdateDialog(group)} />
              <IconButton icon="g1-delete" size={32} onClick={getHandleDeleteClick(group)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default AccessManagerGroupsTable;
