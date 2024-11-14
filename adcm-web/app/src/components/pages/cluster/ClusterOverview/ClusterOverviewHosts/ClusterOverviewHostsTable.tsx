import { Statusable, Table, TableCell, TableRow, Tooltip } from '@uikit';
import type { AdcmClusterOverviewStatusHost } from '@models/adcm';
import { AdcmClusterStatus } from '@models/adcm';
import s from './ClusterOverviewHosts.module.scss';
import { Link, useParams } from 'react-router-dom';

interface clusterOverviewHostsTableProps {
  hosts: AdcmClusterOverviewStatusHost[];
}

const ClusterOverviewHostsTable = ({ hosts }: clusterOverviewHostsTableProps) => {
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  return (
    <Table variant="secondary">
      {hosts.map((host) => {
        const hostStatus = host.status === AdcmClusterStatus.Up ? 'done' : 'unknown';

        return (
          <TableRow key={host.id}>
            <TableCell>
              <Tooltip label={host.name} placement="top-start">
                <Statusable className={s.clusterOverviewHosts__title} status={hostStatus} size="medium">
                  <Link to={`/clusters/${clusterId}/hosts/${host.id}`} className="text-link">
                    {host.name}
                  </Link>
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
