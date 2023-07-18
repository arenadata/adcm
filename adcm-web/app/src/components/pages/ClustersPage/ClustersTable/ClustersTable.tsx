import { Link } from 'react-router-dom';
import { Table, TableRow, TableCell } from '@uikit';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { useStore } from '@hooks';
import { columns, clusterStatusesMap } from './ClustersTable.constants';

const ClustersTable = () => {
  const { clusters } = useStore((s) => s.adcm.clusters);

  return (
    <Table columns={columns}>
      {clusters.map((cluster) => {
        return (
          <TableRow key={cluster.id}>
            <StatusableCell status={clusterStatusesMap[cluster.status]}>
              <Link to={`/clusters/${cluster.name}`}>{cluster.name}</Link>
            </StatusableCell>
            <TableCell>{cluster.state}</TableCell>
            <TableCell>{cluster.prototypeName}</TableCell>
            <TableCell>{cluster.prototypeVersion}</TableCell>
            <TableCell>{cluster.description}</TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default ClustersTable;
