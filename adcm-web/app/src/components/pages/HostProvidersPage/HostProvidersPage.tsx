import React from 'react';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import HostProviderTable from '@pages/HostProvidersPage/HostProviderTable/HostProviderTable';
import { useRequestHostProviders } from '@pages/HostProvidersPage/useRequestHostProviders';
import HostProviderTableToolbar from '@pages/HostProvidersPage/HostProviderTableToolbar/HostProviderTableToolbar';
import HostProviderTableFooter from '@pages/HostProvidersPage/HostProviderTableFooter/HostProviderTableFooter';
import HostProvidersActionsDialogs from '@pages/HostProvidersPage/HostProvidersActionsDialogs/HostProvidersActionsDialogs';

const HostProvidersPage = () => {
  useRequestHostProviders();

  return (
    <TableContainer variant="easy">
      <HostProviderTableToolbar />
      <HostProviderTable />
      <HostProviderTableFooter />
      <HostProvidersActionsDialogs />
    </TableContainer>
  );
};

export default HostProvidersPage;
