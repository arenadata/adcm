import { Link } from 'react-router-dom';
import { Table, TableRow, TableCell, IconButton } from '@uikit';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { useDispatch, useStore } from '@hooks';
import { columns, serviceComponentsStatusMap } from './ServiceComponentsTable.constants';
import { setSortParams } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsTableSlice';
import { SortParams } from '@uikit/types/list.types';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';
import { openMaintenanceModeDialog } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsActionsSlice';
import { AdcmServiceComponent } from '@models/adcm';

const ServiceComponentsTable = () => {
  const dispatch = useDispatch();
  const components = useStore((s) => s.adcm.serviceComponents.serviceComponents);
  const isLoading = useStore((s) => s.adcm.serviceComponents.isLoading);
  const sortParams = useStore((s) => s.adcm.serviceComponentsTable.sortParams);

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const handleClickMaintenanceMode = (component: AdcmServiceComponent) => () => {
    if (component.isMaintenanceModeAvailable) {
      dispatch(openMaintenanceModeDialog(component.id));
    }
  };

  const dummyHandler = () => {
    console.info('implement actions please!');
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {components.map((component) => {
        return (
          <TableRow key={component.id}>
            <StatusableCell status={serviceComponentsStatusMap[component.status]}>
              <Link
                className="text-link"
                to={`/clusters/${component.cluster.id}/services/${component.service.id}/components/${component.id}/`}
              >
                {component.displayName}
              </Link>
            </StatusableCell>
            <TableCell>
              <Link className="text-link" to={`/clusters/${component.cluster.id}/hosts/`}>
                {component.hosts.length} {component.hosts.length === 1 ? 'host' : 'hosts'}
              </Link>
            </TableCell>
            <TableCell hasIconOnly>
              <Concern concerns={component.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-actions" size={32} onClick={() => dummyHandler()} title="Actions" />
              <MaintenanceModeButton
                isMaintenanceModeAvailable={component.isMaintenanceModeAvailable}
                maintenanceModeStatus={component.maintenanceMode}
                onClick={handleClickMaintenanceMode(component)}
              />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default ServiceComponentsTable;
