import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { IconButton, Table, TableCell, TableRow } from '@uikit';
import { columns, hostStatusesMap } from '@pages/cluster/ClusterHosts/ClusterHostsTable/ClusterHostsTable.constant';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { orElseGet } from '@utils/checkUtils.ts';
import UnlinkHostToggleButton from '@pages/HostsPage/HostsTable/Buttons/UnlinkHostToggleButton/UnlinkHostToggleButton';
import { setSortParams } from '@store/adcm/cluster/hosts/hostsTableSlice';
import { SortParams } from '@models/table';
import { AdcmClusterHost } from '@models/adcm/clusterHosts';

const ClusterHostsTable: React.FC = () => {
  const dispatch = useDispatch();

  const clusterHosts = useStore(({ adcm }) => adcm.clusterHosts.hosts);
  const isLoading = useStore(({ adcm }) => adcm.clusterHosts.isLoading);
  const sortParams = useStore((s) => s.adcm.clusterHostsTable.sortParams);

  const dummyHandler = () => () => {
    console.info('Add proper action handlers');
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {clusterHosts.map((clusterHost: AdcmClusterHost) => {
        return (
          <TableRow key={clusterHost.id}>
            <StatusableCell status={hostStatusesMap['done']}>{clusterHost.name}</StatusableCell>
            <TableCell>{clusterHost.state}</TableCell>
            <TableCell>{clusterHost.hostprovider.name}</TableCell>
            <TableCell>{`${clusterHost.components.length} components`}</TableCell>
            <TableCell>{'-'}</TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-actions" size={32} onClick={dummyHandler()} title="Actions" />
              <IconButton icon="g1-maintenance" size={32} onClick={dummyHandler()} title="Maintenance mode" />
              <UnlinkHostToggleButton host={clusterHost} />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default ClusterHostsTable;
