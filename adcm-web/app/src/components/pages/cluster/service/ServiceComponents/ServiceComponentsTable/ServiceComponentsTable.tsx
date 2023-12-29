import { Link } from 'react-router-dom';
import { Table, TableRow, TableCell } from '@uikit';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { useDispatch, useStore } from '@hooks';
import { columns, serviceComponentsStatusMap } from './ServiceComponentsTable.constants';
import { setSortParams } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsTableSlice';
import { SortParams } from '@uikit/types/list.types';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';
import { openMaintenanceModeDialog } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsActionsSlice';
import { AdcmServiceComponent } from '@models/adcm';
import ClusterServiceComponentsDynamicActionsIcon from '../ServiceComponentsDynamicActionsIcon/ServiceComponentsDynamicActionsIcon';
import { usePersistServiceComponentsTableSettings } from '../usePersistServiceComponentsTableSettings';
import { isShowSpinner } from '@uikit/Table/Table.utils';

const ServiceComponentsTable = () => {
  const dispatch = useDispatch();
  const components = useStore((s) => s.adcm.serviceComponents.serviceComponents);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.serviceComponents.loadState));
  const sortParams = useStore((s) => s.adcm.serviceComponentsTable.sortParams);

  usePersistServiceComponentsTableSettings();

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const handleClickMaintenanceMode = (component: AdcmServiceComponent) => () => {
    if (component.isMaintenanceModeAvailable) {
      dispatch(openMaintenanceModeDialog(component.id));
    }
  };

  return (
    <Table
      isLoading={isLoading}
      columns={columns}
      sortParams={sortParams}
      onSorting={handleSorting}
      variant="secondary"
      dataTest="service-component-table"
    >
      {components.map((component) => {
        return (
          <TableRow key={component.id}>
            <StatusableCell status={serviceComponentsStatusMap[component.status]}>
              <Link
                className="text-link"
                to={`/clusters/${component.cluster.id}/services/${component.service.id}/components/${component.id}`}
              >
                {component.displayName}
              </Link>
            </StatusableCell>
            <TableCell>
              <Link className="text-link" to={`/clusters/${component.cluster.id}/hosts`}>
                {component.hosts.length} {component.hosts.length === 1 ? 'host' : 'hosts'}
              </Link>
            </TableCell>
            <TableCell hasIconOnly>
              <Concern concerns={component.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              {component && <ClusterServiceComponentsDynamicActionsIcon component={component} />}
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
