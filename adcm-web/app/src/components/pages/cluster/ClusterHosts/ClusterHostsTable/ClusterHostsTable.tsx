import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { Table, TableCell, TableRow } from '@uikit';
import { columns, hostStatusesMap } from '@pages/cluster/ClusterHosts/ClusterHostsTable/ClusterHostsTable.constant';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import UnlinkHostToggleButton from '@pages/cluster/ClusterHosts/ClusterHostsTable/Buttons/UnlinkHostToggleButton/UnlinkHostToggleButton';
import { setSortParams } from '@store/adcm/cluster/hosts/hostsTableSlice';
import { SortParams } from '@models/table';
import { AdcmClusterHost } from '@models/adcm/clusterHosts';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';
import { openMaintenanceModeDialog } from '@store/adcm/cluster/hosts/hostsActionsSlice';
import { Link, generatePath } from 'react-router-dom';
import ClusterHostsDynamicActionsButton from '../ClusterHostsDynamicActionsButton/ClusterHostsDynamicActionsButton';

const ClusterHostsTable: React.FC = () => {
  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const clusterHosts = useStore(({ adcm }) => adcm.clusterHosts.hosts);
  const isLoading = useStore(({ adcm }) => adcm.clusterHosts.isLoading);
  const sortParams = useStore((s) => s.adcm.clusterHostsTable.sortParams);

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };
  const handleClickMaintenanceMode = (host: AdcmClusterHost) => () => {
    if (host.isMaintenanceModeAvailable) {
      dispatch(openMaintenanceModeDialog(host));
    }
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {clusterHosts.map((clusterHost: AdcmClusterHost) => {
        return (
          <TableRow key={clusterHost.id}>
            <StatusableCell status={hostStatusesMap[clusterHost.status]}>
              <Link
                className="text-link"
                to={generatePath('/clusters/:clusterId/hosts/:hostId', {
                  clusterId: `${clusterHost.cluster.id}`,
                  hostId: `${clusterHost.id}`,
                })}
              >
                {clusterHost.name}
              </Link>
            </StatusableCell>
            <TableCell>{clusterHost.state}</TableCell>
            <TableCell>
              <Link className="text-link" to={`/hostproviders/${clusterHost.hostprovider.id}`}>
                {clusterHost.hostprovider.name}
              </Link>
            </TableCell>
            <TableCell>
              <Link
                className="text-link"
                to={generatePath('/clusters/:clusterId/hosts/:hostId', {
                  clusterId: `${clusterHost.cluster.id}`,
                  hostId: `${clusterHost.id}`,
                })}
              >
                {clusterHost.components.length} {clusterHost.components.length === 1 ? 'component' : 'components'}
              </Link>
            </TableCell>
            <TableCell>{'-'}</TableCell>
            <TableCell hasIconOnly align="center">
              {cluster && <ClusterHostsDynamicActionsButton cluster={cluster} host={clusterHost} type="icon" />}
              <MaintenanceModeButton
                isMaintenanceModeAvailable={clusterHost.isMaintenanceModeAvailable}
                maintenanceModeStatus={clusterHost.maintenanceMode}
                onClick={handleClickMaintenanceMode(clusterHost)}
              />
              <UnlinkHostToggleButton host={clusterHost} />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default ClusterHostsTable;
