import { useDispatch, useStore } from '@hooks';
import { columns } from '@pages/HostProvidersPage/HostProviderTable/HostProviderTable.constants';
import { IconButton, Table, TableCell, TableRow } from '@uikit';
import { orElseGet } from '@utils/checkUtils';
import { openDeleteDialog } from '@store/adcm/hostProviders/hostProvidersActionsSlice';
import { setSortParams } from '@store/adcm/hostProviders/hostProvidersTableSlice';
import { SortParams } from '@models/table';
import Concern from '@commonComponents/Concern/Concern';
import { Link } from 'react-router-dom';

const HostProviderTable = () => {
  const dispatch = useDispatch();

  const hostProviders = useStore(({ adcm }) => adcm.hostProviders.hostProviders);
  const isLoading = useStore(({ adcm }) => adcm.hostProviders.isLoading);
  const sortParams = useStore(({ adcm }) => adcm.hostProvidersTable.sortParams);

  const handleDeleteAction = (id: number) => {
    dispatch(openDeleteDialog(id));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {hostProviders.map((hostProvider) => (
        <TableRow key={hostProvider.id}>
          <TableCell>
            <Link to={`/hostproviders/${hostProvider.id}`}>{hostProvider.name}</Link>
          </TableCell>
          <TableCell>{hostProvider.prototype.displayName}</TableCell>
          <TableCell>{hostProvider.prototype.version}</TableCell>
          <TableCell>{hostProvider.state}</TableCell>
          <TableCell>{orElseGet(hostProvider.description)}</TableCell>
          <TableCell>
            <Concern concerns={hostProvider.concerns} />
          </TableCell>
          <TableCell hasIconOnly align="center">
            <IconButton
              disabled={!hostProvider.isUpgradable}
              icon="g1-actions"
              size={32}
              onClick={() => null}
              title="Upgrade"
            />
            <IconButton
              disabled={!hostProvider.isUpgradable}
              icon="g1-upgrade"
              size={32}
              onClick={() => null}
              title="Upgrade"
            />
            <IconButton icon="g1-delete" size={32} onClick={() => handleDeleteAction(hostProvider.id)} title="Delete" />
          </TableCell>
        </TableRow>
      ))}
    </Table>
  );
};

export default HostProviderTable;
