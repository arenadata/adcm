import { Link } from 'react-router-dom';
import { Table, TableRow, TableCell, IconButton, Button } from '@uikit';
import Concern from '@commonComponents/Concern/Concern';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { useStore } from '@hooks';
import { columns, serviceComponentStatusMap } from './ServiceComponentTable.constants';
import ServiceComponentMaintenanceModeButton from './ServiceComponentMaintenanceModeButton/ServiceComponentMaintenanceModeButton';

interface ServiceComponentTableProps {
  onClick: () => void;
  showConfig: () => void;
  isConfigShown: boolean;
}

const ServiceComponentTable: React.FC<ServiceComponentTableProps> = ({ onClick, showConfig, isConfigShown }) => {
  const serviceComponent = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);
  const isLoading = useStore(({ adcm }) => adcm.serviceComponent.isLoading);

  const dummyHandler = () => {
    console.info('implement actions please!');
  };

  return (
    <Table columns={columns} isLoading={isLoading}>
      {serviceComponent && (
        <TableRow>
          <StatusableCell status={serviceComponentStatusMap[serviceComponent.status]}>
            <Link className="text-link" to="#" onClick={showConfig}>
              {serviceComponent?.displayName}
            </Link>
          </StatusableCell>
          <TableCell>
            <Link className="text-link" to={`/clusters/${serviceComponent.cluster.id}/hosts/`}>
              {serviceComponent.hosts.length} {serviceComponent?.hosts.length === 1 ? 'host' : 'hosts'}
            </Link>
          </TableCell>
          <TableCell hasIconOnly>
            <Concern concerns={serviceComponent.concerns} />
          </TableCell>
          <TableCell hasIconOnly align="center">
            <IconButton icon="g1-actions" size={32} onClick={() => dummyHandler()} title="Actions" />
            <ServiceComponentMaintenanceModeButton />
          </TableCell>
          <TableCell>
            <Button iconRight="g2-back" onClick={onClick} disabled={!isConfigShown} variant="secondary" />
          </TableCell>
        </TableRow>
      )}
    </Table>
  );
};

export default ServiceComponentTable;
