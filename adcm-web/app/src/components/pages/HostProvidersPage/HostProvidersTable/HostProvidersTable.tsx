import { useDispatch, useStore } from '@hooks';
import { columns } from '@pages/HostProvidersPage/HostProvidersTable/HostProvidersTable.constants';
import { IconButton, Table, TableCell, TableRow } from '@uikit';
import { orElseGet } from '@utils/checkUtils';
import { openDeleteDialog } from '@store/adcm/hostProviders/hostProvidersActionsSlice';
import { setSortParams } from '@store/adcm/hostProviders/hostProvidersTableSlice';
import type { SortParams } from '@models/table';
import Concern from '@commonComponents/Concern/Concern';
import { Link } from 'react-router-dom';
import MultiStateCell from '@commonComponents/Table/Cells/MultiStateCell';
import HostProvidersDynamicActionsIcon from '../HostProvidersDynamicActionsIcon/HostProvidersDynamicActionsIcon';
import type { AdcmHostProvider } from '@models/adcm';
import { opeHostProviderUpgradeDialog } from '@store/adcm/hostProviders/hostProviderUpgradesSlice';
import { isShowSpinner } from '@uikit/Table/Table.utils';
import { isBlockingConcernPresent } from '@utils/concernUtils.ts';

const HostProviderTable = () => {
  const dispatch = useDispatch();

  const hostProviders = useStore(({ adcm }) => adcm.hostProviders.hostProviders);
  const isLoading = useStore(({ adcm }) => isShowSpinner(adcm.hostProviders.loadState));
  const sortParams = useStore(({ adcm }) => adcm.hostProvidersTable.sortParams);

  const handleDeleteAction = (hostProvider: AdcmHostProvider) => {
    dispatch(openDeleteDialog(hostProvider));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const handleUpgradeClick = (hostProviders: AdcmHostProvider) => {
    dispatch(opeHostProviderUpgradeDialog(hostProviders));
  };

  return (
    <Table
      isLoading={isLoading}
      columns={columns}
      sortParams={sortParams}
      onSorting={handleSorting}
      variant="secondary"
    >
      {hostProviders.map((hostProvider) => (
        <TableRow key={hostProvider.id}>
          <TableCell>
            <Link to={`/hostproviders/${hostProvider.id}`} className="text-link">
              {hostProvider.name}
            </Link>
          </TableCell>
          <TableCell>{hostProvider.prototype.displayName}</TableCell>
          <TableCell>{hostProvider.prototype.version}</TableCell>
          <MultiStateCell entity={hostProvider} />
          <TableCell>{orElseGet(hostProvider.description)}</TableCell>
          <TableCell hasIconOnly>
            <Concern concerns={hostProvider.concerns} />
          </TableCell>
          <TableCell hasIconOnly align="center">
            <HostProvidersDynamicActionsIcon hostProvider={hostProvider} />
            <IconButton
              icon="g1-upgrade"
              size={32}
              disabled={!hostProvider.isUpgradable || isBlockingConcernPresent(hostProvider.concerns)}
              onClick={() => handleUpgradeClick(hostProvider)}
              title={hostProvider.isUpgradable ? 'Upgrade' : 'No upgrades'}
            />
            <IconButton icon="g1-delete" size={32} onClick={() => handleDeleteAction(hostProvider)} title="Delete" />
          </TableCell>
        </TableRow>
      ))}
    </Table>
  );
};

export default HostProviderTable;
