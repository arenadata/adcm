import { Link } from 'react-router-dom';
import { AdcmCluster, AdcmEntitySystemState } from '@models/adcm';
import { Table, TableRow, TableCell, IconButton } from '@uikit';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { useDispatch, useStore } from '@hooks';
import { columns, clusterStatusesMap } from './ClustersTable.constants';
import {
  openClusterUpgradeDialog,
  openClusterDeleteDialog,
  openClusterRenameDialog,
} from '@store/adcm/clusters/clustersActionsSlice';
import { setSortParams } from '@store/adcm/clusters/clustersTableSlice';
import { SortParams } from '@uikit/types/list.types';
import ClusterDynamicActionsIcon from '@pages/ClustersPage/ClustersTable/ClusterDynamicActionsIcon/ClusterDynamicActionsIcon';
import MultiStateCell from '@commonComponents/Table/Cells/MultiStateCell';

const ClustersTable = () => {
  const dispatch = useDispatch();
  const clusters = useStore((s) => s.adcm.clusters.clusters);
  const isLoading = useStore((s) => s.adcm.clusters.isLoading);
  const sortParams = useStore((s) => s.adcm.clustersTable.sortParams);

  const handleUpgradeClick = (cluster: AdcmCluster) => {
    dispatch(openClusterUpgradeDialog({ cluster }));
  };

  const getHandleDeleteClick = (clusterId: number) => () => {
    dispatch(openClusterDeleteDialog(clusterId));
  };

  const handleRenameClick = (cluster: AdcmCluster) => {
    dispatch(openClusterRenameDialog(cluster));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {clusters.map((cluster) => {
        return (
          <TableRow key={cluster.id}>
            <StatusableCell status={clusterStatusesMap[cluster.status]}>
              <Link to={`/clusters/${cluster.id}`}>{cluster.name}</Link>
              {cluster.state === AdcmEntitySystemState.Created && (
                <IconButton icon="g1-edit" size={32} title="Edit" onClick={() => handleRenameClick(cluster)} />
              )}
            </StatusableCell>
            <MultiStateCell entity={cluster} />
            <TableCell>{cluster.prototype.displayName}</TableCell>
            <TableCell>{cluster.prototype.version}</TableCell>
            <TableCell>{cluster.description}</TableCell>
            <TableCell hasIconOnly>
              <Concern concerns={cluster.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              <ClusterDynamicActionsIcon cluster={cluster} />
              <IconButton
                icon="g1-upgrade"
                size={32}
                disabled={!cluster.isUpgradable}
                onClick={() => handleUpgradeClick(cluster)}
              />
              <IconButton icon="g1-delete" size={32} onClick={getHandleDeleteClick(cluster.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default ClustersTable;
