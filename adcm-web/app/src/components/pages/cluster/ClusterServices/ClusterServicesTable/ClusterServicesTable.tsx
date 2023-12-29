import { Link, useParams } from 'react-router-dom';
import { Table, TableRow, TableCell, IconButton } from '@uikit';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { useDispatch, useStore } from '@hooks';
import { columns, servicesStatusesMap } from './ClusterServicesTable.constants';
import { setSortParams } from '@store/adcm/cluster/services/servicesTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { openDeleteDialog } from '@store/adcm/cluster/services/servicesActionsSlice';
import ClusterServiceDynamicActionsButton from '@pages/cluster/ClusterServices/ClusterServiceDynamicActionsButton/ClusterServiceDynamicActionsButton';
import MultiStateCell from '@commonComponents/Table/Cells/MultiStateCell';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';
import { AdcmService } from '@models/adcm';
import { openMaintenanceModeDialog } from '@store/adcm/cluster/services/servicesActionsSlice';
import { isShowSpinner } from '@uikit/Table/Table.utils';

const ClusterServicesTable = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const services = useStore((s) => s.adcm.services.services);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.services.loadState));
  const sortParams = useStore((s) => s.adcm.servicesTable.sortParams);
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const isAddingServices = useStore(({ adcm }) => adcm.servicesActions.isAddingServices);

  const getHandleDeleteClick = (serviceId: number) => () => {
    dispatch(openDeleteDialog(serviceId));
  };

  const handleClickMaintenanceMode = (service: AdcmService) => () => {
    if (service.isMaintenanceModeAvailable) {
      dispatch(openMaintenanceModeDialog(service));
    }
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table
      isLoading={isLoading || isAddingServices}
      columns={columns}
      sortParams={sortParams}
      onSorting={handleSorting}
      variant="secondary"
    >
      {services.map((service) => {
        return (
          <TableRow key={service.id}>
            <StatusableCell status={servicesStatusesMap[service.status]}>
              <Link to={`/clusters/${clusterId}/services/${service.id}`} className="text-link">
                {service.displayName}
              </Link>
            </StatusableCell>
            <TableCell>{service.prototype.version}</TableCell>
            <MultiStateCell entity={service} />
            <TableCell hasIconOnly>
              <Concern concerns={service.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              {cluster && <ClusterServiceDynamicActionsButton cluster={cluster} service={service} type="icon" />}
              <MaintenanceModeButton
                isMaintenanceModeAvailable={service.isMaintenanceModeAvailable}
                maintenanceModeStatus={service.maintenanceMode}
                onClick={handleClickMaintenanceMode(service)}
              />
              <IconButton icon="g1-delete" size={32} onClick={getHandleDeleteClick(service.id)} title="Delete" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default ClusterServicesTable;
