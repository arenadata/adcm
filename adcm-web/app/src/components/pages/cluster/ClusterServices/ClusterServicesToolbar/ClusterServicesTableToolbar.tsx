import { Button } from '@uikit';
import ClusterServicesFilters from './ClusterServicesTableFilters';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import { openServiceAddDialog } from '@store/adcm/cluster/services/servicesActionsSlice';
import { useParams } from 'react-router-dom';
import { useDispatch } from '@hooks';

const ClustersTableHeader = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const handleAddClusterServiceClick = () => {
    dispatch(openServiceAddDialog(clusterId));
  };

  return (
    <TableToolbar>
      <ClusterServicesFilters />
      <Button onClick={handleAddClusterServiceClick}>Add service</Button>
    </TableToolbar>
  );
};

export default ClustersTableHeader;
