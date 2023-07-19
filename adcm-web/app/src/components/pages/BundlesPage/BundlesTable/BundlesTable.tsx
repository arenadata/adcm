import React, { Dispatch, SetStateAction, useCallback } from 'react';
import { useDispatch, useStore } from '@hooks';
import { bundleSignatureStatusesMap, columns } from './BundlesTable.constants';
import { Checkbox, IconButton, Table, TableCell, TableRow } from '@uikit';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { orElseGet } from '@utils/checkUtils';
import { useSelectedRows } from '@uikit/Table/useSelectedRows';
import { AdcmBundle } from '@models/adcm/bundle';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { getStatusLabel } from '@utils/humanizationUtils';
import { setDeletableId, setSelectedItemsIds as setSelectedBundlesIds } from '@store/adcm/bundles/bundlesTableSlice';

const getBundleUniqKey = ({ id }: AdcmBundle) => id;

const BundlesTable: React.FC = () => {
  const dispatch = useDispatch();

  const bundles = useStore(({ adcm }) => adcm.bundles.bundles);
  const isLoading = useStore(({ adcm }) => adcm.bundles.isLoading);
  const selectedItemsIds = useStore(({ adcm }) => adcm.bundlesTable.selectedItemsIds);

  const setSelectedItemsIds = useCallback<Dispatch<SetStateAction<number[]>>>(
    (arg) => {
      const value = typeof arg === 'function' ? arg(selectedItemsIds) : arg;
      dispatch(setSelectedBundlesIds(value));
    },
    [dispatch, selectedItemsIds],
  );

  const { isAllItemsSelected, toggleSelectedAllItems, getHandleSelectedItem, isItemSelected } = useSelectedRows(
    bundles,
    getBundleUniqKey,
    selectedItemsIds,
    setSelectedItemsIds,
  );

  const getHandleDeleteClick = (bundleId: number) => () => {
    // set deletable id for show Delete Confirm Dialog
    dispatch(setDeletableId(bundleId));
  };

  return (
    <Table
      isLoading={isLoading}
      columns={columns}
      variant="tertiary"
      isAllSelected={isAllItemsSelected}
      toggleSelectedAll={toggleSelectedAllItems}
    >
      {bundles.map((bundle) => {
        return (
          <TableRow key={bundle.id}>
            <TableCell>
              <Checkbox checked={isItemSelected(bundle)} onChange={getHandleSelectedItem(bundle)} />
            </TableCell>
            <TableCell>{bundle.displayName}</TableCell>
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
