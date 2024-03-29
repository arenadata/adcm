import { Statusable, Table, TableCell, TableRow, Tooltip } from '@uikit';
import { AdcmClusterOverviewStatusHost, AdcmClusterStatus } from '@models/adcm';
import s from './ClusterOverviewHosts.module.scss';
import { Link } from 'react-router-dom';

interface clusterOverviewHostsTableProps {
  hosts: AdcmClusterOverviewStatusHost[];
}

const ClusterOverviewHostsTable = ({ hosts }: clusterOverviewHostsTableProps) => {
  return (
    <Table variant="secondary">
      {hosts.map((host) => {
        const hostStatus = host.status === AdcmClusterStatus.Up ? 'done' : 'unknown';

        return (
          <TableRow key={host.id}>
            <TableCell>
              <Tooltip label={host.name} placement="top-start">
                <Statusable className={s.clusterOverviewHosts__title} status={hostStatus} size="medium">
                  <Link to={`/hosts/${host.id}`}>{host.name}</Link>
                </Statusable>
              </Tooltip>
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default ClusterOverviewHostsTable;
