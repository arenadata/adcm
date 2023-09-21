import { Link, useParams } from 'react-router-dom';
import { Table, TableRow, TableCell, IconButton } from '@uikit';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { useDispatch, useStore } from '@hooks';
import { columns, servicesStatusesMap } from './ClusterServicesTable.constants';
import { setSortParams } from '@store/adcm/clusters/clustersTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { openDeleteDialog } from '@store/adcm/cluster/services/servicesActionsSlice';
import ClusterServiceDynamicActionsButton from '@pages/cluster/ClusterServices/ClusterServiceDynamicActionsButton/ClusterServiceDynamicActionsButton';
import MultiStateCell from '@commonComponents/Table/Cells/MultiStateCell';

const ClusterServicesTable = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const services = useStore((s) => s.adcm.services.services);
  const isLoading = useStore((s) => s.adcm.services.isLoading);
  const sortParams = useStore((s) => s.adcm.servicesTable.sortParams);
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  const getHandleDeleteClick = (serviceId: number) => () => {
    dispatch(openDeleteDialog(serviceId));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {services.map((service) => {
        return (
          <TableRow key={service.id}>
            <StatusableCell status={servicesStatusesMap[service.status]}>
              <Link to={`/clusters/${clusterId}/services/${service.id}`}>{service.name}</Link>
            </StatusableCell>
            <TableCell>{service.prototype.version}</TableCell>
            <MultiStateCell entity={service} />
            <TableCell hasIconOnly>
              <Concern concerns={service.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              {cluster && <ClusterServiceDynamicActionsButton cluster={cluster} service={service} type="icon" />}
              <IconButton icon="g1-delete" size={32} onClick={getHandleDeleteClick(service.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default ClusterServicesTable;
