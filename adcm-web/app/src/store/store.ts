import { configureStore, combineReducers } from '@reduxjs/toolkit';
import authSlice from '@store/authSlice';
import notificationsSlice from '@store/notificationsSlice';
import clustersSlice from '@store/adcm/clusters/clustersSlice';
import clustersDynamicActionsSlice from '@store/adcm/clusters/clustersDynamicActionsSlice';
import clusterHostsSlice from '@store/adcm/cluster/hosts/hostsSlice';
import clusterHostsTableSlice from '@store/adcm/cluster/hosts/hostsTableSlice';
import clusterHostsActionsSlice from '@store/adcm/cluster/hosts/hostsActionsSlice';
import clusterHostsDynamicActionsSlice from '@store/adcm/cluster/hosts/hostsDynamicActionsSlice';
import clustersTableSlice from '@store/adcm/clusters/clustersTableSlice';
import bundlesSlice from '@store/adcm/bundles/bundlesSlice';
import bundleSlice from '@store/adcm/bundle/bundleSlice';
import bundlesTableSlice from '@store/adcm/bundles/bundlesTableSlice';
import clusterMappingSlice from '@store/adcm/cluster/mapping/mappingSlice';
import breadcrumbsSlice from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import hostProvidersSlice from '@store/adcm/hostProviders/hostProvidersSlice';
import hostProvidersTableSlice from '@store/adcm/hostProviders/hostProvidersTableSlice';
import createHostProviderDialogSlice from '@store/adcm/hostProviders/dialogs/createHostProviderDialogSlice';
import hostsTableSlice from '@store/adcm/hosts/hostsTableSlice';
import hostsSlice from '@store/adcm/hosts/hostsSlice';
import hostsActionsSlice from '@store/adcm/hosts/hostsActionsSlice';
import serviceSlice from '@store/adcm/services/serviceSlice';
import auditOperationsSlice from '@store/adcm/audit/auditOperations/auditOperationsSlice';
import auditOperationsTableSlice from '@store/adcm/audit/auditOperations/auditOperationsTableSlice';
import auditLoginsSlice from '@store/adcm/audit/auditLogins/auditLoginsSlice';
import auditLoginsTableSlice from '@store/adcm/audit/auditLogins/auditLoginsTableSlice';
import clusterImportsSlice from '@store/adcm/cluster/imports/cluster/clusterImportsSlice';
import clusterImportsFilterSlice from '@store/adcm/cluster/imports/cluster/clusterImportsFilterSlice';
import clusterImportsServiceSlice from '@store/adcm/cluster/imports/service/clusterImportsServiceSlice';
import clusterImportsServiceFilterSlice from '@store/adcm/cluster/imports/service/clusterImportsServiceFilterSlice';
import clusterOverviewServicesSlice from '@store/adcm/cluster/overview/overviewServicesSlice';
import clusterOverviewHostsSlice from '@store/adcm/cluster/overview/overviewHostsSlice';
import clusterOverviewServicesTableSlice from '@store/adcm/cluster/overview/overviewServicesTableSlice';
import clusterOverviewHostsTableSlice from '@store/adcm/cluster/overview/overviewHostsTableSlice';

import { apiMiddleware } from './middlewares/apiMiddleware';
import clusterSlice from './adcm/clusters/clusterSlice';
import usersSlice from './adcm/users/usersSlice';
import usersTableSlice from './adcm/users/usersTableSlice';
import createUserDialogSlice from './adcm/users/dialogs/createUserDialogSlice';
import servicesSlice from './adcm/cluster/services/servicesSlice';
import servicesTableSlice from './adcm/cluster/services/servicesTableSlice';
import servicesActionsSlice from './adcm/cluster/services/servicesActionsSlice';
import servicesDynamicActionsSlice from './adcm/cluster/services/servicesDynamicActionsSlice';
import serviceComponentsSlice from './adcm/cluster/services/serviceComponents/serviceComponentsSlice';
import serviceComponentsTableSlice from './adcm/cluster/services/serviceComponents/serviceComponentsTableSlice';
import usersActionsSlice from './adcm/users/usersActionsSlice';
import jobsSlice from './adcm/jobs/jobsSlice';
import jobsTableSlice from './adcm/jobs/jobsTableSlice';
import jobsActionsSlice from './adcm/jobs/jobsActionsSlice';
import groupsSlice from './adcm/groups/groupsSlice';
import groupsTableSlice from './adcm/groups/groupsTableSlice';
import groupsActionsSlice from './adcm/groups/groupActionsSlice';
import policiesTableSlice from './adcm/policies/policiesTableSlice';
import policiesSlice from './adcm/policies/policiesSlice';
import policiesActionsSlice from './adcm/policies/policiesActionsSlice';
import rolesSlice from './adcm/roles/rolesSlice';
import rolesTableSlice from './adcm/roles/rolesTableSlice';
import rolesActionsSlice from './adcm/roles/rolesActionsSlice';
import serviceComponentsActionsSlice from './adcm/cluster/services/serviceComponents/serviceComponentsActionsSlice';
import serviceComponentSlice from './adcm/cluster/services/serviceComponents/serviceComponent/serviceComponentSlice';
import clustersActionsSlice from './adcm/clusters/clustersActionsSlice';
import clusterHostSlice from './adcm/cluster/hosts/host/clusterHostSlice';
import clusterHostTableSlice from './adcm/cluster/hosts/host/clusterHostTableSlice';
import profileSlice from './adcm/profile/profileSlice';
import hostsDynamicActionsSlice from './adcm/hosts/hostsDynamicActionsSlice';

const rootReducer = combineReducers({
  auth: authSlice,
  notifications: notificationsSlice,
  adcm: combineReducers({
    cluster: clusterSlice,
    clusters: clustersSlice,
    clustersActions: clustersActionsSlice,
    clustersDynamicActions: clustersDynamicActionsSlice,
    clustersTable: clustersTableSlice,
    clusterHosts: clusterHostsSlice,
    clusterHost: clusterHostSlice,
    clusterHostTable: clusterHostTableSlice,
    clusterHostsActions: clusterHostsActionsSlice,
    clusterHostsDynamicActions: clusterHostsDynamicActionsSlice,
    clusterHostsTable: clusterHostsTableSlice,
    clusterMapping: clusterMappingSlice,
    bundle: bundleSlice,
    bundles: bundlesSlice,
    bundlesTable: bundlesTableSlice,
    breadcrumbs: breadcrumbsSlice,
    hostProviders: hostProvidersSlice,
    hostProvidersTable: hostProvidersTableSlice,
    createHostProviderDialog: createHostProviderDialogSlice,
    hosts: hostsSlice,
    hostsTable: hostsTableSlice,
    hostsActions: hostsActionsSlice,
    hostsDynamicActions: hostsDynamicActionsSlice,
    service: serviceSlice,
    services: servicesSlice,
    servicesTable: servicesTableSlice,
    servicesActions: servicesActionsSlice,
    servicesDynamicActions: servicesDynamicActionsSlice,
    serviceComponents: serviceComponentsSlice,
    serviceComponentsTable: serviceComponentsTableSlice,
    serviceComponentsActions: serviceComponentsActionsSlice,
    serviceComponent: serviceComponentSlice,
    auditOperations: auditOperationsSlice,
    auditOperationsTable: auditOperationsTableSlice,
    auditLogins: auditLoginsSlice,
    auditLoginsTable: auditLoginsTableSlice,
    clusterImports: clusterImportsSlice,
    clusterImportsFilter: clusterImportsFilterSlice,
    clusterImportsService: clusterImportsServiceSlice,
    clusterImportsServiceFilter: clusterImportsServiceFilterSlice,
    clusterOverviewServices: clusterOverviewServicesSlice,
    clusterOverviewHosts: clusterOverviewHostsSlice,
    clusterOverviewServicesTable: clusterOverviewServicesTableSlice,
    clusterOverviewHostsTable: clusterOverviewHostsTableSlice,
    // createHostDialog: createHostDialogSlice,
    users: usersSlice,
    usersTable: usersTableSlice,
    usersActions: usersActionsSlice,
    createUserDialog: createUserDialogSlice,
    jobs: jobsSlice,
    jobsTable: jobsTableSlice,
    jobsActions: jobsActionsSlice,
    groups: groupsSlice,
    groupsTable: groupsTableSlice,
    groupsActions: groupsActionsSlice,
    policies: policiesSlice,
    policiesActions: policiesActionsSlice,
    policiesTable: policiesTableSlice,
    profile: profileSlice,
    roles: rolesSlice,
    rolesTable: rolesTableSlice,
    rolesActions: rolesActionsSlice,
  }),
});

export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiMiddleware),
});

export type StoreState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;
