import React, { Dispatch, SetStateAction, useCallback } from 'react';
import { useDispatch, useStore } from '@hooks';
import { bundleSignatureStatusesMap, columns } from './BundlesTable.constants';
import { Checkbox, IconButton, Table, TableCell, TableRow } from '@uikit';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { orElseGet } from '@utils/checkUtils';
import { useSelectedItems } from '@uikit/hooks/useSelectedItems';
import { AdcmBundle } from '@models/adcm/bundle';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { getStatusLabel } from '@utils/humanizationUtils';
import { setDeletableId, setSelectedItemsIds as setSelectedBundlesIds } from '@store/adcm/bundles/bundlesSlice';
import { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/bundles/bundlesTableSlice';
import { Link } from 'react-router-dom';

const getBundleUniqKey = ({ id }: AdcmBundle) => id;

const BundlesTable: React.FC = () => {
  const dispatch = useDispatch();

  const bundles = useStore(({ adcm }) => adcm.bundles.bundles);
  const isLoading = useStore(({ adcm }) => adcm.bundles.isLoading);
  const selectedItemsIds = useStore(({ adcm }) => adcm.bundles.selectedItemsIds);
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
    dispatch(setDeletableId(bundleId));
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
          <TableRow key={bundle.id}>
            <TableCell>
              <Checkbox checked={isItemSelected(bundle)} onChange={getHandlerSelectedItem(bundle)} />
            </TableCell>
            <TableCell>
              <Link to={`/bundles/${bundle.id}`}>{bundle.displayName || bundle.name}</Link>
            </TableCell>
            <TableCell>{bundle.version}</TableCell>
            <TableCell>{orElseGet(bundle.edition)}</TableCell>
            <DateTimeCell value={bundle.uploadTime} />
            <StatusableCell status={bundleSignatureStatusesMap[bundle.signatureStatus]}>
              {getStatusLabel(bundle.signatureStatus)}
            </StatusableCell>
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
