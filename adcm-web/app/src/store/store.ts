import { configureStore, combineReducers } from '@reduxjs/toolkit';
import userSlice from '@store/userSlice';
import notificationsSlice from '@store/notificationsSlice';
import clustersSlice from '@store/adcm/clusters/clustersSlice';
import clustersTableSlice from '@store/adcm/clusters/clustersTableSlice';
import createClusterDialogSlice from '@store/adcm/clusters/dialogs/createClusterDialogSlice';
import bundlesSlice from '@store/adcm/bundles/bundlesSlice';
import bundlesTableSlice from '@store/adcm/bundles/bundlesTableSlice';
import breadcrumbsSlice from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import hostProvidersSlice from '@store/adcm/hostProviders/hostProvidersSlice';
import hostProvidersTableSlice from '@store/adcm/hostProviders/hostProvidersTableSlice';

import { apiMiddleware } from './middlewares/apiMiddleware';
import clusterSlice from './adcm/clusters/clusterSlice';

const rootReducer = combineReducers({
  user: userSlice,
  notifications: notificationsSlice,
  adcm: combineReducers({
    cluster: clusterSlice,
    clusters: clustersSlice,
    clustersTable: clustersTableSlice,
    createClusterDialog: createClusterDialogSlice,
    bundles: bundlesSlice,
    bundlesTable: bundlesTableSlice,
    breadcrumbs: breadcrumbsSlice,
    hostProviders: hostProvidersSlice,
    hostProvidersTable: hostProvidersTableSlice,
  }),
});

export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiMiddleware),
});

export type StoreState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;
