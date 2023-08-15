import React from 'react';
import { Provider } from 'react-redux';
import './scss/app.scss';
import { store } from '@store';
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import LoginPage from '@pages/LoginPage/LoginPage';
import ClustersPage from '@pages/ClustersPage/ClustersPage';
import HostProvidersPage from '@pages/HostProvidersPage/HostProvidersPage';
import HostsPage from '@pages/HostsPage/HostsPage';
import JobsPage from '@pages/JobsPage/JobsPage';
import AccessManagerPage from '@pages/AccessManagerPage/AccessManagerPage';
import AuditPageLayout from '@layouts/AuditPageLayout/AuditPageLayout';
import AuditOperationsPage from '@pages/audit/AuditOperationsPage/AuditOperationsPage';
import AuditLoginsPage from '@pages/audit/AuditLoginsPage/AuditLoginsPage';
import BundlesPage from '@pages/BundlesPage/BundlesPage';
import PrivateResource from '@commonComponents/PrivateResource/PrivateResource';
import MainLayout from '@layouts/MainLayout/MainLayout';
import ProfilePage from '@pages/ProfilePage/ProfilePage';
import SettingsPage from '@pages/SettingsPage/SettingsPage';
import UserSession from '@commonComponents/UserSession/UserSession';
import ClusterPageLayout from '@layouts/ClusterPageLayout/ClusterPageLayout';

import {
  ClusterConfiguration,
  ClusterHosts,
  ClusterImport,
  ClusterImportsCluster,
  ClusterImportsService,
  ClusterMapping,
  ClusterHostsMapping,
  ClusterComponentsMapping,
  ClusterOverview,
  ClusterServices,
} from '@pages/cluster';
import ClusterServiceLayout from '@layouts/ClusterServiceLayout/ClusterServiceLayout';
import {
  ServiceComponents,
  ServiceConfigurationGroups,
  ServiceInfo,
  ServicePrimaryConfiguration,
} from '@pages/cluster/service';
import AccessManagerUsersPage from '@pages/AccessManagerPage/AccessManagerUsersPage/AccessManagerUsersPage';
import AccessManagerGroupsPage from '@pages/AccessManagerPage/AccessManagerGroupsPage/AccessManagerGroupsPage';
import AccessManagerRolesPage from '@pages/AccessManagerPage/AccessManagerRolesPage/AccessManagerRolesPage';
import AccessManagerPolicyPage from '@pages/AccessManagerPage/AccessManagerPolicyPage/AccessManagerPolicyPage';
import BundleOverviewPage from '@pages/BundleOverviewPage/BundleOverviewPage';

function App() {
  return (
    <BrowserRouter>
      <Provider store={store}>
        <UserSession>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <PrivateResource>
                  <MainLayout>
                    <Outlet />
                  </MainLayout>
                </PrivateResource>
              }
            >
              <Route index element={<Navigate to="/clusters/" replace />} />
              {/**
                URLs in old design have template `/entity` but in new design - `/entities`.
                And some Main Info (which write in bundles) have links with old URLs on inner pages
               */}
              <Route path="/cluster/" element={<Navigate to="/clusters/" replace />} />
              <Route path="/clusters/">
                <Route index element={<ClustersPage />} />
                <Route path="/clusters/:clusterId" element={<ClusterPageLayout />}>
                  <Route index element={<Navigate to="overview" replace />} />
                  <Route path="/clusters/:clusterId/overview" element={<ClusterOverview />} />
                  <Route path="/clusters/:clusterId/services">
                    <Route index element={<ClusterServices />} />
                    <Route path="/clusters/:clusterId/services/:serviceId" element={<ClusterServiceLayout />}>
                      <Route index element={<Navigate to="primary-configuration" replace />} />
                      <Route
                        path="/clusters/:clusterId/services/:serviceId/primary-configuration"
                        element={<ServicePrimaryConfiguration />}
                      />
                      <Route
                        path="/clusters/:clusterId/services/:serviceId/configuration-groups"
                        element={<ServiceConfigurationGroups />}
                      />
                      <Route
                        path="/clusters/:clusterId/services/:serviceId/components"
                        element={<ServiceComponents />}
                      />
                      <Route path="/clusters/:clusterId/services/:serviceId/info" element={<ServiceInfo />} />
                    </Route>
                  </Route>
                  <Route path="/clusters/:clusterId/hosts" element={<ClusterHosts />} />
                  <Route path="/clusters/:clusterId/mapping" element={<ClusterMapping />}>
                    <Route index element={<Navigate to="hosts" replace />} />
                    <Route path="/clusters/:clusterId/mapping/hosts" element={<ClusterHostsMapping />} />
                    <Route path="/clusters/:clusterId/mapping/components" element={<ClusterComponentsMapping />} />
                  </Route>
                  <Route path="/clusters/:clusterId/configuration" element={<ClusterConfiguration />} />
                  <Route path="/clusters/:clusterId/import" element={<ClusterImport />}>
                    <Route index element={<Navigate to="cluster" replace />} />
                    <Route path="/clusters/:clusterId/import/cluster" element={<ClusterImportsCluster />} />
                    <Route path="/clusters/:clusterId/import/services" element={<ClusterImportsService />} />
                  </Route>
                </Route>
              </Route>

              <Route path="/hostproviders" element={<HostProvidersPage />} />
              <Route path="/hosts" element={<HostsPage />} />
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/access-manager" element={<AccessManagerPage />}>
                <Route index element={<Navigate to="/access-manager/users" replace />} />
                <Route path="/access-manager/users" element={<AccessManagerUsersPage />} />
                <Route path="/access-manager/groups" element={<AccessManagerGroupsPage />} />
                <Route path="/access-manager/roles" element={<AccessManagerRolesPage />} />
                <Route path="/access-manager/policy" element={<AccessManagerPolicyPage />} />
              </Route>
              <Route path="/audit" element={<AuditPageLayout />}>
                <Route index element={<Navigate to="/audit/operations" replace />} />
                <Route path="/audit/operations" element={<AuditOperationsPage />} />
                <Route path="/audit/logins" element={<AuditLoginsPage />} />
              </Route>
              <Route path="/bundles" element={<BundlesPage />} />
              <Route path="/bundles/:bundleId" element={<BundleOverviewPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </UserSession>
      </Provider>
    </BrowserRouter>
  );
}

export default App;
