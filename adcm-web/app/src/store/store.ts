import { configureStore, combineReducers } from '@reduxjs/toolkit';
import userSlice from '@store/userSlice';
import notificationsSlice from '@store/notificationsSlice';
import clustersSlice from '@store/adcm/clusters/clustersSlice';
import clustersTableSlice from '@store/adcm/clusters/clustersTableSlice';
import createClusterDialogSlice from '@store/adcm/clusters/dialogs/createClusterDialogSlice';
import bundlesSlice from '@store/adcm/bundles/bundlesSlice';
import bundlesTableSlice from '@store/adcm/bundles/bundlesTableSlice';
import hostProvidersSlice from '@store/adcm/hostProviders/hostProvidersSlice';
import hostProvidersTableSlice from '@store/adcm/hostProviders/hostProvidersTableSlice';
import createHostProviderDialogSlice from '@store/adcm/hostProviders/dialogs/createHostProviderDialogSlice';
import hostsTableSlice from '@store/adcm/hosts/hostsTableSlice.tsx';
import hostsSlice from '@store/adcm/hosts/hostsSlice.tsx';

import { apiMiddleware } from './middlewares/apiMiddleware';

const rootReducer = combineReducers({
  user: userSlice,
  notifications: notificationsSlice,
  adcm: combineReducers({
    clusters: clustersSlice,
    clustersTable: clustersTableSlice,
    createClusterDialog: createClusterDialogSlice,
    bundles: bundlesSlice,
    bundlesTable: bundlesTableSlice,
    hostProviders: hostProvidersSlice,
    hostProvidersTable: hostProvidersTableSlice,
    createHostProviderDialog: createHostProviderDialogSlice,
    hosts: hostsSlice,
    hostsTable: hostsTableSlice,
    // createHostDialog: createHostDialogSlice,
  }),
});

export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiMiddleware),
});

export type StoreState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;
