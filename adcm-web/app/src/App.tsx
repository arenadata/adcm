import React from 'react';
import './scss/app.scss';
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import LoginPage from '@pages/LoginPage/LoginPage';
import ClustersPage from '@pages/ClustersPage/ClustersPage';
import HostProvidersPage from '@pages/HostProvidersPage/HostProvidersPage';
import HostsPage from '@pages/HostsPage/HostsPage';
import JobsPage from '@pages/JobsPage/JobsPage';
import AccessManagerPage from '@pages/AccessManagerPage/AccessManagerPage';
import AuditPage from '@pages/AuditPage/AuditPage';
import BundlesPage from '@pages/BundlesPage/BundlesPage';
import PrivateResource from '@commonComponents/PrivateResource/PrivateResource';
import MainLayout from '@layouts/MainLayout/MainLayout';
import ProfilePage from '@pages/ProfilePage/ProfilePage';
import SettingsPage from '@pages/SettingsPage/SettingsPage';
import ClusterOverview from '@pages/ClustersPage/ClusterOverview/ClusterOverview';

function App() {
  return (
    <BrowserRouter>
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
          <Route index element={<Navigate to="/clusters" replace />} />

          <Route path="/clusters">
            <Route index element={<ClustersPage />} />
            <Route path="/clusters/:clusterName">
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="/clusters/:clusterName/overview" element={<ClusterOverview />} />
            </Route>
          </Route>

          <Route path="/hostproviders" element={<HostProvidersPage />} />
          <Route path="/hosts" element={<HostsPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/access-manager" element={<AccessManagerPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/bundles" element={<BundlesPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
