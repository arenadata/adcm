import { Dispatch, SetStateAction, useCallback } from 'react';
import { Link, generatePath } from 'react-router-dom';
import { Table, TableRow, TableCell, IconButton, Checkbox } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './AccessManagerGroupsTable.constants';
import { setDeletableId, setSelectedItemsIds as setSelectedIds } from '@store/adcm/groups/groupsSlice';
import { setSortParams } from '@store/adcm/groups/groupsTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { AdcmGroup } from '@models/adcm';
import { useSelectedItems } from '@uikit/hooks/useSelectedItems';
import { ACCESS_MANAGER_PAGE_URLS } from '@pages/AccessManagerPage/AccessManagerPage.constants';

const AccessManagerGroupsTable = () => {
  const dispatch = useDispatch();
  const { groups, isLoading, selectedItemsIds } = useStore((s) => s.adcm.groups);
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
    dispatch(setDeletableId(id));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table
      isLoading={isLoading}
      columns={columns}
      sortParams={sortParams}
      onSorting={handleSorting}
      isAllSelected={isAllItemsSelected}
      toggleSelectedAll={toggleSelectedAllItems}
    >
      {groups.map((group) => {
        return (
          <TableRow key={group.id}>
            <TableCell>
              <Checkbox checked={isItemSelected(group)} onChange={getHandlerSelectedItem(group)} />
            </TableCell>
            <TableCell>
              <Link to={generatePath(ACCESS_MANAGER_PAGE_URLS.Group, { groupId: group.id + '' })}>
                {group.displayName}
              </Link>
            </TableCell>
            <TableCell>{group.description}</TableCell>
            <TableCell>{group.users.map((user) => user.username).join(', ')}</TableCell>
            <TableCell>{group.type}</TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-edit" size={32} title="Edit" />
              <IconButton icon="g1-delete" size={32} onClick={getHandleDeleteClick(group.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default AccessManagerGroupsTable;
