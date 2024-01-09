import React from 'react';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { serviceComponentsStatusMap } from '@pages/cluster/service/ServiceComponents/ServiceComponentsTable/ServiceComponentsTable.constants';
import { Table, TableCell, TableRow } from '@uikit';
import { Link, generatePath, useParams } from 'react-router-dom';
import { columns } from './HostComponentsTable.constants';
import { SortParams } from '@uikit/types/list.types';
import { useDispatch, useStore } from '@hooks';
import HostComponentsDynamicActionsIcon from './HostComponentsDynamicActionsIcon/HostComponentsDynamicActionsIcon';
import { setSortParams } from '@store/adcm/hostComponents/hostComponentsTableSlice';
import { isShowSpinner } from '@uikit/Table/Table.utils';

const HostComponentsTable: React.FC = () => {
  const dispatch = useDispatch();
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);
  const hostComponents = useStore((s) => s.adcm.hostComponents.hostComponents);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.hostComponents.loadState));
  const sortParams = useStore((s) => s.adcm.hostComponentsTable.sortParams);

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table
      isLoading={isLoading}
      columns={columns}
      sortParams={sortParams}
      onSorting={handleSorting}
      variant="secondary"
    >
      {hostComponents.map((hostComponent) => {
        return (
          <TableRow key={hostComponent.id}>
            <StatusableCell status={serviceComponentsStatusMap[hostComponent.status]} size="medium">
              <Link
                className="text-link"
                to={generatePath('/clusters/:clusterId/services/:serviceId/components/:componentId', {
                  clusterId: `${hostComponent.cluster.id}`,
                  serviceId: `${hostComponent.service.id}`,
                  componentId: `${hostComponent.id}`,
                })}
              >
                {hostComponent.displayName}
              </Link>
            </StatusableCell>
            <TableCell hasIconOnly>
              <Concern concerns={hostComponent.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              {hostComponent && hostId && (
                <HostComponentsDynamicActionsIcon component={hostComponent} hostId={hostId} />
              )}
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default HostComponentsTable;
