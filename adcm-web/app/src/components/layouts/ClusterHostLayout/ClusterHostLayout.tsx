import type React from 'react';
import { Outlet } from 'react-router-dom';
import ClusterHostHeader from './ClusterHostHeader/ClusterHostHeader';
import ClusterHostNavigation from './ClusterHostNavigation/ClusterHostNavigation';
import { useRequestClusterHost } from './useRequestHost';
import ClusterHostsDynamicActionDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/ClusterHostsDynamicActionDialog/ClusterHostsDynamicActionDialog';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';
import ClusterHostsDynamicActionWizardDialog from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/ClusterHostsDynamicActionWizardDialog/ClusterHostsDynamicActionWizardDialog';

const ClusterHostLayout: React.FC = () => {
  const { accessCheckStatus } = useRequestClusterHost();

  return (
    <div>
      <PermissionsChecker requestState={accessCheckStatus}>
        <ClusterHostHeader />
        <ClusterHostNavigation />
        <Outlet />
        <ClusterHostsDynamicActionDialog />
        <ClusterHostsDynamicActionWizardDialog />
      </PermissionsChecker>
    </div>
  );
};

export default ClusterHostLayout;
