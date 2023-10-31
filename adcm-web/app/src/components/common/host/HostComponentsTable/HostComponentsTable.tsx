import React from 'react';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { serviceComponentsStatusMap } from '@pages/cluster/service/ServiceComponents/ServiceComponentsTable/ServiceComponentsTable.constants';
import { Table, TableCell, TableRow } from '@uikit';
import { Link, generatePath, useParams } from 'react-router-dom';
import { columns } from './HostComponentsTable.constants';
import { SortParams } from '@uikit/types/list.types';
import { useDispatch, useStore } from '@hooks';
import { setSortParams } from '@store/adcm/cluster/hosts/host/clusterHostTableSlice';
import HostComponentsDynamicActionsIcon from '@commonComponents/host/HostComponentsDynamicActionsIcon/HostComponentsDynamicActionsIcon';

const HostComponentsTable: React.FC = () => {
  const dispatch = useDispatch();
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);
  const hostComponents = useStore((s) => s.adcm.clusterHost.relatedData.hostComponents);
  const isLoading = useStore((s) => s.adcm.clusterHost.isLoading);
  const sortParams = useStore((s) => s.adcm.clusterHostTable.sortParams);

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {hostComponents.map((hostComponent) => {
        return (
          <TableRow key={hostComponent.id}>
            <StatusableCell status={serviceComponentsStatusMap[hostComponent.status]}>
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
