import { Dispatch, SetStateAction, useCallback } from 'react';
import { Table, TableRow, TableCell, IconButton, Checkbox } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './AccessManagerGroupsTable.constants';
import { openDeleteDialog, setSelectedItemsIds as setSelectedIds } from '@store/adcm/groups/groupActionsSlice';
import { setSortParams } from '@store/adcm/groups/groupsTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { AdcmGroup } from '@models/adcm';
import { useSelectedItems } from '@uikit/hooks/useSelectedItems';
import { openUpdateDialog } from '@store/adcm/groups/groupActionsSlice';
import { isShowSpinner } from '@uikit/Table/Table.utils';

const AccessManagerGroupsTable = () => {
  const dispatch = useDispatch();
  const groups = useStore((s) => s.adcm.groups.groups);
  const selectedItemsIds = useStore((s) => s.adcm.groupsActions.selectedItemsIds);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.groups.loadState));
  const sortParams = useStore((s) => s.adcm.groupsTable.sortParams);

  const setSelectedItemsIds = useCallback<Dispatch<SetStateAction<number[]>>>(
    (arg) => {
      const value = typeof arg === 'function' ? arg(selectedItemsIds) : arg;
      dispatch(setSelectedIds(value));
    },
    [dispatch, selectedItemsIds],
  );

  const getUniqKey = ({ id }: AdcmGroup) => id;
  const { isAllItemsSelected, toggleSelectedAllItems, getHandlerSelectedItem, isItemSelected } = useSelectedItems(
    groups,
    getUniqKey,
    selectedItemsIds,
    setSelectedItemsIds,
  );

  const getHandleDeleteClick = (id: number) => () => {
    dispatch(openDeleteDialog(id));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const handleOpenUpdateDialog = (group: AdcmGroup) => () => {
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
              <IconButton icon="g1-edit" size={32} title="Edit" onClick={handleOpenUpdateDialog(group)} />
              <IconButton icon="g1-delete" size={32} onClick={getHandleDeleteClick(group.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default AccessManagerGroupsTable;
