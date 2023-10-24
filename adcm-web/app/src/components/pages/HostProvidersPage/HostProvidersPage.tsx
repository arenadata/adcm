import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import HostProvidersTable from '@pages/HostProvidersPage/HostProvidersTable/HostProvidersTable';
import { useRequestHostProviders } from '@pages/HostProvidersPage/useRequestHostProviders';
import HostProvidersTableToolbar from '@pages/HostProvidersPage/HostProviderTableToolbar/HostProviderTableToolbar';
import HostProvidersTableFooter from '@pages/HostProvidersPage/HostProvidersTableFooter/HostProvidersTableFooter';
import Dialogs from '@pages/HostProvidersPage/Dialogs';

const HostProvidersPage = () => {
  useRequestHostProviders();

  return (
    <TableContainer variant="easy">
      <HostProvidersTableToolbar />
      <HostProvidersTable />
      <HostProvidersTableFooter />
      <Dialogs />
    </TableContainer>
  );
};

export default HostProvidersPage;
