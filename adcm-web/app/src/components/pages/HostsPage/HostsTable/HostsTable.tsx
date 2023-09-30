import React from 'react';
import { IconButton, Table, TableCell, TableRow } from '@uikit';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { columns, hostStatusesMap } from '@pages/HostsPage/HostsTable/HostsTable.constants';
import { useDispatch, useStore } from '@hooks';
import { AdcmHost } from '@models/adcm/host';
import UnlinkHostToggleButton from '@pages/HostsPage/HostsTable/Buttons/UnlinkHostToggleButton/UnlinkHostToggleButton';
import { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/hosts/hostsTableSlice';
import { orElseGet } from '@utils/checkUtils';
import { openDeleteDialog, openMaintenanceModeDialog } from '@store/adcm/hosts/hostsActionsSlice';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';
import HostDynamicActionsIcon from '../HostDynamicActionsIcon/HostDynamicActionsIcon';
import MultiStateCell from '@commonComponents/Table/Cells/MultiStateCell';
import Concern from '@commonComponents/Concern/Concern';

const HostsTable: React.FC = () => {
  const dispatch = useDispatch();

  const hosts = useStore(({ adcm }) => adcm.hosts.hosts);
  const isLoading = useStore(({ adcm }) => adcm.hosts.isLoading);
  const sortParams = useStore((s) => s.adcm.hostsTable.sortParams);

  const handleClickMaintenanceMode = (host: AdcmHost) => () => {
    if (host.isMaintenanceModeAvailable) {
      dispatch(openMaintenanceModeDialog(host.id));
    }
  };

  const getHandleDeleteClick = (hostId: number) => () => {
    // set deletable id for show Delete Confirm Dialog
    dispatch(openDeleteDialog(hostId));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {hosts.map((host: AdcmHost) => {
        return (
          <TableRow key={host.id}>
            <StatusableCell status={hostStatusesMap[host.status]}>{host.name}</StatusableCell>
            <MultiStateCell entity={host} />
            <TableCell>{host.hostprovider.name}</TableCell>
            <TableCell>{orElseGet(host.cluster?.name)}</TableCell>
            <TableCell>
              <Concern concerns={host.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              <HostDynamicActionsIcon host={host} />
              <MaintenanceModeButton
                isMaintenanceModeAvailable={host.isMaintenanceModeAvailable}
                maintenanceModeStatus={host.maintenanceMode}
                onClick={handleClickMaintenanceMode(host)}
              />
              <UnlinkHostToggleButton host={host} />
              <IconButton icon="g1-delete" size={32} onClick={getHandleDeleteClick(host.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default HostsTable;
