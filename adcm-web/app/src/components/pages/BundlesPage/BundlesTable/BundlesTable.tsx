import React, { Dispatch, SetStateAction, useCallback } from 'react';
import { useDispatch, useStore } from '@hooks';
import { columns } from './BundlesTable.constants';
import { Checkbox, IconButton, Table, TableCell, TableRow } from '@uikit';
import { orElseGet } from '@utils/checkUtils';
import { useSelectedItems } from '@uikit/hooks/useSelectedItems';
import { AdcmBundle } from '@models/adcm';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import {
  openDeleteDialog,
  setSelectedItemsIds as setSelectedBundlesIds,
} from '@store/adcm/bundles/bundlesActionsSlice';
import { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/bundles/bundlesTableSlice';
import { Link } from 'react-router-dom';
import cn from 'classnames';
import { isShowSpinner } from '@uikit/Table/Table.utils';

const getBundleUniqKey = ({ id }: AdcmBundle) => id;

const BundlesTable: React.FC = () => {
  const dispatch = useDispatch();

  const bundles = useStore(({ adcm }) => adcm.bundles.bundles);
  const isLoading = useStore(({ adcm }) => isShowSpinner(adcm.bundles.loadState));
  const selectedItemsIds = useStore(({ adcm }) => adcm.bundlesActions.selectedItemsIds);
  const sortParams = useStore((s) => s.adcm.bundlesTable.sortParams);

  const setSelectedItemsIds = useCallback<Dispatch<SetStateAction<number[]>>>(
    (arg) => {
      const value = typeof arg === 'function' ? arg(selectedItemsIds) : arg;
      dispatch(setSelectedBundlesIds(value));
    },
    [dispatch, selectedItemsIds],
  );

  const { isAllItemsSelected, toggleSelectedAllItems, getHandlerSelectedItem, isItemSelected } = useSelectedItems(
    bundles,
    getBundleUniqKey,
    selectedItemsIds,
    setSelectedItemsIds,
  );

  const getHandleDeleteClick = (bundleId: number) => () => {
    // set deletable id for show Delete Confirm Dialog
    dispatch(openDeleteDialog(bundleId));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table
      isLoading={isLoading}
      columns={columns}
      variant="tertiary"
      sortParams={sortParams}
      onSorting={handleSorting}
      isAllSelected={isAllItemsSelected}
      toggleSelectedAll={toggleSelectedAllItems}
    >
      {bundles.map((bundle) => {
        return (
          <TableRow key={bundle.id} className={cn({ 'is-selected': selectedItemsIds.includes(bundle.id) })}>
            <TableCell>
              <Checkbox checked={isItemSelected(bundle)} onChange={getHandlerSelectedItem(bundle)} />
            </TableCell>
            <TableCell>
              <Link to={`/bundles/${bundle.id}`}>{bundle.displayName || bundle.name}</Link>
            </TableCell>
            <TableCell>{bundle.version}</TableCell>
            <TableCell>{orElseGet(bundle.edition)}</TableCell>
            <DateTimeCell value={bundle.uploadTime} />
            <TableCell>{bundle.mainPrototype.license.status}</TableCell>
            <TableCell>{bundle.signatureStatus}</TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-delete" size={32} onClick={getHandleDeleteClick(bundle.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default BundlesTable;
