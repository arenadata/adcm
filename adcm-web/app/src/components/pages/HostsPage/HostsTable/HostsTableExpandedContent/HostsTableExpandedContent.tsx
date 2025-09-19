import Concern from '@commonComponents/Concern/Concern';
import type { AdcmHostDuplicate } from '@models/adcm';
import { IconButton, Table, TableCell, TableRow } from '@uikit';
import { orElseGet } from '@utils/checkUtils';
import type React from 'react';
import { Link } from 'react-router-dom';
import { columns } from './HostsTableExpandedContent.constants';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';
import { useDispatch } from '@hooks';
import { openDeleteDialog, openMaintenanceModeDialog } from '@store/adcm/hosts/hostsActionsSlice';
import UnlinkHostDuplicateToggleButton from './UnlinkHostDuplicateToggleButton/UnlinkHostDuplicateToggleButton';

interface HostsTableExpandedContentProps {
  duplicates: AdcmHostDuplicate[];
}

const HostsTableExpandedContent: React.FC<HostsTableExpandedContentProps> = ({ duplicates }) => {
  const dispatch = useDispatch();

  const handleClickMaintenanceMode = (host: AdcmHostDuplicate) => () => {
    if (host.isMaintenanceModeAvailable) {
      dispatch(openMaintenanceModeDialog(host));
    }
  };

  const getHandleDeleteClick = (host: AdcmHostDuplicate) => () => {
    dispatch(openDeleteDialog(host));
  };

  return (
    <Table columns={columns} variant="secondary">
      {duplicates.map((host: AdcmHostDuplicate) => {
        const isHostLinked = !!host.cluster?.id;

        return (
          <TableRow key={host.id}>
            <TableCell>
              <Link to={`/hosts/${host.id}`} className="text-link">
                {host.name}
              </Link>
            </TableCell>
            <TableCell>
              {orElseGet(host.cluster, (cluster) => (
                <Link to={`/clusters/${cluster.id}`} className="text-link">
                  {cluster.name}
                </Link>
              ))}
            </TableCell>
            <TableCell hasIconOnly>
              <Concern concerns={host.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              <MaintenanceModeButton
                isMaintenanceModeAvailable={host.isMaintenanceModeAvailable}
                maintenanceModeStatus={host.maintenanceMode}
                onClick={handleClickMaintenanceMode(host)}
              />
              <UnlinkHostDuplicateToggleButton host={host} />
              <IconButton
                icon="g1-delete"
                size={32}
                disabled={isHostLinked}
                onClick={getHandleDeleteClick(host)}
                title={isHostLinked ? 'Unlink the duplicate to enable the Delete button' : 'Delete'}
              />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default HostsTableExpandedContent;
