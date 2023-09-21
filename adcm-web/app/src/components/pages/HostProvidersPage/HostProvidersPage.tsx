import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import HostProviderTable from '@pages/HostProvidersPage/HostProviderTable/HostProviderTable';
import { useRequestHostProviders } from '@pages/HostProvidersPage/useRequestHostProviders';
import HostProviderTableToolbar from '@pages/HostProvidersPage/HostProviderTableToolbar/HostProviderTableToolbar';
import HostProviderTableFooter from '@pages/HostProvidersPage/HostProviderTableFooter/HostProviderTableFooter';
import HostProvidersActionsDialogs from '@pages/HostProvidersPage/HostProvidersActionsDialogs/HostProvidersActionsDialogs';
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
      <HostProviderTableToolbar />
      <HostProviderTable />
      <HostProviderTableFooter />
      <HostProvidersActionsDialogs />
      <Dialogs />
    </TableContainer>
  );
};

export default HostProvidersPage;
