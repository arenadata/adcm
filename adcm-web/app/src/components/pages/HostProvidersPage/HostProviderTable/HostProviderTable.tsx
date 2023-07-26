import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { columns } from '@pages/HostProvidersPage/HostProviderTable/HostProviderTable.constants';
import { IconButton, Table, TableCell, TableRow } from '@uikit';
import { orElseGet } from '@utils/checkUtils';
import { setDeletableId } from '@store/adcm/hostProviders/hostProvidersSlice';
import { setSortParams } from '@store/adcm/hostProviders/hostProvidersTableSlice';
import { SortParams } from '@models/table';

const HostProviderTable = () => {
  const dispatch = useDispatch();

  const hostProviders = useStore(({ adcm }) => adcm.hostProviders.hostProviders);
  const isLoading = useStore(({ adcm }) => adcm.hostProviders.isLoading);
  const sortParams = useStore(({ adcm }) => adcm.hostProvidersTable.sortParams);

  const handleDeleteAction = (id: number) => {
    dispatch(setDeletableId(id));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {hostProviders.map((hostProvider) => (
        <TableRow key={hostProvider.id}>
          <TableCell>{hostProvider.name}</TableCell>
          <TableCell>{hostProvider.prototype.displayName}</TableCell>
          <TableCell>{hostProvider.prototype.version}</TableCell>
          <TableCell>{hostProvider.state}</TableCell>
          <TableCell>{orElseGet(hostProvider.description)}</TableCell>
          <TableCell>-</TableCell>
          <TableCell hasIconOnly align="center">
            <IconButton
              disabled={!hostProvider.isUpgradable}
              icon="g1-actions"
              size={32}
              onClick={() => null}
              title="Upgrade"
            />
            <IconButton
              disabled={!hostProvider.isUpgradable}
              icon="g1-upgrade"
              size={32}
              onClick={() => null}
              title="Upgrade"
            />
            <IconButton icon="g1-delete" size={32} onClick={() => handleDeleteAction(hostProvider.id)} title="Delete" />
          </TableCell>
        </TableRow>
      ))}
    </Table>
  );
};

export default HostProviderTable;
