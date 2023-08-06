import { configureStore, combineReducers } from '@reduxjs/toolkit';
import userSlice from '@store/userSlice';
import notificationsSlice from '@store/notificationsSlice';
import clustersSlice from '@store/adcm/clusters/clustersSlice';
import clustersTableSlice from '@store/adcm/clusters/clustersTableSlice';
import createClusterDialogSlice from '@store/adcm/clusters/dialogs/createClusterDialogSlice';
import upgradeClusterDialogSlice from '@store/adcm/clusters/dialogs/upgradeClusterDialogSlice';
import bundlesSlice from '@store/adcm/bundles/bundlesSlice';
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

import { apiMiddleware } from './middlewares/apiMiddleware';
import clusterSlice from './adcm/clusters/clusterSlice';
import usersSlice from './adcm/users/usersSlice';
import usersTableSlice from './adcm/users/usersTableSlice';

const rootReducer = combineReducers({
  user: userSlice,
  notifications: notificationsSlice,
  adcm: combineReducers({
    cluster: clusterSlice,
    clusters: clustersSlice,
    clustersTable: clustersTableSlice,
    createClusterDialog: createClusterDialogSlice,
    clusterMapping: clusterMappingSlice,
    upgradeClusterDialog: upgradeClusterDialogSlice,
    bundles: bundlesSlice,
    bundlesTable: bundlesTableSlice,
    breadcrumbs: breadcrumbsSlice,
    hostProviders: hostProvidersSlice,
    hostProvidersTable: hostProvidersTableSlice,
    createHostProviderDialog: createHostProviderDialogSlice,
    hosts: hostsSlice,
    hostsTable: hostsTableSlice,
    hostsActions: hostsActionsSlice,
    service: serviceSlice,
    auditOperations: auditOperationsSlice,
    auditOperationsTable: auditOperationsTableSlice,
    auditLogins: auditLoginsSlice,
    auditLoginsTable: auditLoginsTableSlice,
    // createHostDialog: createHostDialogSlice,
    users: usersSlice,
    usersTable: usersTableSlice,
  }),
});

export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiMiddleware),
});

export type StoreState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;
