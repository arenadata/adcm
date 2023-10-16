import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import HostProvidersTable from '@pages/HostProvidersPage/HostProvidersTable/HostProvidersTable';
import { useRequestHostProviders } from '@pages/HostProvidersPage/useRequestHostProviders';
import HostProvidersTableToolbar from '@pages/HostProvidersPage/HostProviderTableToolbar/HostProviderTableToolbar';
import HostProvidersTableFooter from '@pages/HostProvidersPage/HostProvidersTableFooter/HostProvidersTableFooter';
import Dialogs from '@pages/HostProvidersPage/Dialogs';
import { useDispatch } from '@hooks';
import { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

const HostProvidersPage = () => {
  useRequestHostProviders();

  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(setBreadcrumbs([]));
  }, [dispatch]);

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
