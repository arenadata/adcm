import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Table, TableCell, ExpandableRowComponent } from '@uikit';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { useDispatch, useStore } from '@hooks';
import { columns, serviceComponentsStatusMap } from './ServiceComponentsTable.constants';
import { setSortParams } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsTableSlice';
import type { SortParams } from '@uikit/types/list.types';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';
import { openMaintenanceModeDialog } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsActionsSlice';
import type { AdcmServiceComponent } from '@models/adcm';
import ClusterServiceComponentsDynamicActionsIcon from '../ServiceComponentsDynamicActionsIcon/ServiceComponentsDynamicActionsIcon';
import { usePersistServiceComponentsTableSettings } from '../usePersistServiceComponentsTableSettings';
import { isShowSpinner } from '@uikit/Table/Table.utils';
import ServiceComponentsTableExpandedContent from './ServiceComponentsTableExpandedContent/ServiceComponentsTableExpandedContent';
import ExpandDetailsCell from '@commonComponents/ExpandDetailsCell/ExpandDetailsCell';

const ServiceComponentsTable = () => {
  const dispatch = useDispatch();
  const components = useStore((s) => s.adcm.serviceComponents.serviceComponents);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.serviceComponents.loadState));
  const sortParams = useStore((s) => s.adcm.serviceComponentsTable.sortParams);

  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});

  usePersistServiceComponentsTableSettings();

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const handleClickMaintenanceMode = (component: AdcmServiceComponent) => () => {
    if (component.isMaintenanceModeAvailable) {
      dispatch(openMaintenanceModeDialog(component.id));
    }
  };

  const handleExpandClick = (id: number) => {
    setExpandableRows({
      ...expandableRows,
      [id]: expandableRows[id] === undefined ? true : !expandableRows[id],
    });
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
          <ExpandableRowComponent
            key={component.id}
            colSpan={columns.length}
            isExpanded={expandableRows[component.id] || false}
            isInactive={!component.hosts.length}
            expandedContent={<ServiceComponentsTableExpandedContent hostComponents={component.hosts || []} />}
          >
            <StatusableCell status={serviceComponentsStatusMap[component.status]}>
              <Link
                className="text-link"
                to={`/clusters/${component.cluster.id}/services/${component.service.id}/components/${component.id}`}
              >
                {component.displayName}
              </Link>
            </StatusableCell>
            <ExpandDetailsCell
              isDisabled={component.hosts.length === 0}
              handleExpandRow={() => handleExpandClick(component.id)}
            >
              <Link className="text-link" to={`/clusters/${component.cluster.id}/hosts?componentId=${component.id}`}>
                {component.hosts.length} {component.hosts.length === 1 ? 'host' : 'hosts'}
              </Link>
            </ExpandDetailsCell>
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
          </ExpandableRowComponent>
        );
      })}
    </Table>
  );
};

export default ServiceComponentsTable;
