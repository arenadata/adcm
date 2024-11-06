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
import { openDeleteDialog, openMaintenanceModeDialog, openUpdateDialog } from '@store/adcm/hosts/hostsActionsSlice';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';
import HostDynamicActionsIcon from '../HostDynamicActionsIcon/HostDynamicActionsIcon';
import MultiStateCell from '@commonComponents/Table/Cells/MultiStateCell';
import Concern from '@commonComponents/Concern/Concern';
import { AdcmEntitySystemState } from '@models/adcm';
import { Link } from 'react-router-dom';
import { isShowSpinner } from '@uikit/Table/Table.utils';

const HostsTable: React.FC = () => {
  const dispatch = useDispatch();

  const hosts = useStore(({ adcm }) => adcm.hosts.hosts);
  const isLoading = useStore(({ adcm }) => isShowSpinner(adcm.hosts.loadState));
  const sortParams = useStore((s) => s.adcm.hostsTable.sortParams);

  const handleClickMaintenanceMode = (host: AdcmHost) => () => {
    if (host.isMaintenanceModeAvailable) {
      dispatch(openMaintenanceModeDialog(host));
    }
  };

  const getHandleDeleteClick = (host: AdcmHost) => () => {
    dispatch(openDeleteDialog(host));
  };

  const handleUpdateClick = (host: AdcmHost) => {
    dispatch(openUpdateDialog(host));
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
      variant="secondary"
    >
      {hosts.map((host: AdcmHost) => {
        const isHostLinked = !!host.cluster?.id;

        return (
          <TableRow key={host.id}>
            <StatusableCell
              status={hostStatusesMap[host.status]}
              endAdornment={
                host.state === AdcmEntitySystemState.Created &&
                !host.cluster?.id && (
                  <IconButton
                    icon="g1-edit"
                    size={32}
                    title="Edit"
                    className="rename-button"
                    onClick={() => handleUpdateClick(host)}
                  />
                )
              }
            >
              <Link to={`/hosts/${host.id}`} className="text-link">
                {host.name}
              </Link>
            </StatusableCell>
            <MultiStateCell entity={host} />
            <TableCell>
              <Link to={`/hostproviders/${host.hostprovider.id}`} className="text-link">
                {host.hostprovider.name}
              </Link>
            </TableCell>
            <TableCell>
              {orElseGet(host.cluster, (cluster) => (
                <Link to={`/clusters/${cluster.id}`} className="text-link">
                  {cluster.name}
                </Link>
              ))}
            </TableCell>
            <TableCell hasIconOnly>
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
              <IconButton
                icon="g1-delete"
                size={32}
                disabled={isHostLinked}
                onClick={getHandleDeleteClick(host)}
                title={isHostLinked ? 'Unlink host to enable Delete button' : 'Delete'}
              />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default HostsTable;
