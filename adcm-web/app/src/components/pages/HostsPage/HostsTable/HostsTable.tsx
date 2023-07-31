import React from 'react';
import { IconButton, Table, TableCell, TableRow } from '@uikit';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { columns, hostStatusesMap } from '@pages/HostsPage/HostsTable/HostsTable.constants';
import { useDispatch, useStore } from '@hooks';
import { AdcmHost } from '@models/adcm/host';
import { setDeletableId } from '@store/adcm/hosts/hostsSlice';
import { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/hosts/hostsTableSlice';
import { orElseGet } from '@utils/checkUtils';

const HostsTable: React.FC = () => {
  const dispatch = useDispatch();

  const hosts = useStore(({ adcm }) => adcm.hosts.hosts);
  const isLoading = useStore(({ adcm }) => adcm.hosts.isLoading);
  const sortParams = useStore((s) => s.adcm.hostsTable.sortParams);

  const dummyHandler = () => () => {
    console.info('Add proper action handlers');
  };

  const getHandleDeleteClick = (hostId: number) => () => {
    // set deletable id for show Delete Confirm Dialog
    dispatch(setDeletableId(hostId));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {hosts.map((host: AdcmHost) => {
        return (
          <TableRow key={host.id}>
            <StatusableCell status={hostStatusesMap['done']}>{host.name}</StatusableCell>
            <TableCell>{host.state}</TableCell>
            <TableCell>{host.provider.name}</TableCell>
            <TableCell>{orElseGet(host.cluster?.name)}</TableCell>
            <TableCell>{'-'}</TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-actions" size={32} onClick={dummyHandler()} title="Actions" />
              <IconButton icon="g1-maintenance" size={32} onClick={dummyHandler()} title="Maintenance mode" />
              <IconButton icon="g1-unlink" size={32} onClick={dummyHandler()} title="Unlink" />
              <IconButton icon="g1-delete" size={32} onClick={getHandleDeleteClick(host.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default HostsTable;
