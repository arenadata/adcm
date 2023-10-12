import { Table, TableRow, TableCell, IconButton } from '@uikit';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { useDispatch, useStore } from '@hooks';
import { columns } from '@pages/cluster/host/HostComponents/HostComponentsTable/HostComponentsTable.constants';
import { SortParams } from '@uikit/types/list.types';
import { serviceComponentsStatusMap } from '@pages/cluster/service/ServiceComponents/ServiceComponentsTable/ServiceComponentsTable.constants';
import { setSortParams } from '@store/adcm/host/hostTableSlice';
import { Link, generatePath } from 'react-router-dom';
import { AdcmServiceComponent } from '@models/adcm';

const HostComponentsTable: React.FC = () => {
  const dispatch = useDispatch();
  const hostComponents = useStore((s) => s.adcm.host.relatedData.hostComponents);
  const isLoading = useStore((s) => s.adcm.host.isLoading);
  const sortParams = useStore((s) => s.adcm.hostTable.sortParams);

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const dummyHandler = () => {
    console.info('implement actions please!');
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {hostComponents.map((hostComponent: AdcmServiceComponent) => {
        return (
          <TableRow key={hostComponent.id}>
            <StatusableCell status={serviceComponentsStatusMap[hostComponent.status]}>
              <Link
                className="text-link"
                to={generatePath('/clusters/:clusterId/services/:serviceId/components', {
                  clusterId: `${hostComponent.cluster.id}`,
                  serviceId: `${hostComponent.service.id}`,
                })}
              >
                {hostComponent.displayName}
              </Link>
            </StatusableCell>
            <TableCell hasIconOnly>
              <Concern concerns={hostComponent.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-actions" size={32} onClick={() => dummyHandler()} title="Actions" />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default HostComponentsTable;
