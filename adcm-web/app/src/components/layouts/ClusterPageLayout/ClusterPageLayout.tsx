import type React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterHeader from '@layouts/ClusterPageLayout/ClusterHeader/ClusterHeader';
import { useRequestCluster } from '@layouts/ClusterPageLayout/useRequestCluster';
import ClusterDynamicActionDialog from '@pages/ClustersPage/Dialogs/ClusterDynamicActionDialog/ClusterDynamicActionDialog';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';

const ClusterPageLayout: React.FC = () => {
  const { accessCheckStatus } = useRequestCluster();

  return (
    <div>
      <PermissionsChecker requestState={accessCheckStatus}>
        <ClusterHeader />
        <Outlet />
        <ClusterDynamicActionDialog />
      </PermissionsChecker>
    </div>
  );
};
export default ClusterPageLayout;
