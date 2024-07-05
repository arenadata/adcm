import { createSlice } from '@reduxjs/toolkit';
import {
  AdcmCluster,
  AdcmHostShortView,
  AdcmMapping,
  AdcmMappingComponent,
  NotAddedServicesDictionary,
} from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { AdcmClusterMappingApi, AdcmClustersApi, RequestError } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showSuccess } from '@store/notificationsSlice';
import { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { ActionStatuses } from '@constants';
import { LoadState } from '@models/loadState';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { arrayToHash } from '@utils/arrayUtils';

type GetClusterMappingArg = {
  clusterId: number;
};

const loadClustersDynamicActions = createAsyncThunk(
  'adcm/clustersDynamicActions/loadClustersDynamicActions',
  async (clustersIds: number[], thunkAPI) => {
    try {
      const actionsPromises = await Promise.allSettled(
        clustersIds.map(async (clusterId) => ({
          clusterId,
          dynamicActions: await AdcmClustersApi.getClusterActions(clusterId),
        })),
      );
      const clustersActions = fulfilledFilter(actionsPromises);
      if (clustersActions.length === 0 && clustersIds.length > 0) {
        throw new Error('All clusters can not get those actions');
      }

      if (clustersActions.length < clustersIds.length) {
        throw new Error('Some clusters can not get those actions');
      }

      return clustersActions.reduce(
        (res, { clusterId, dynamicActions }) => {
          res[clusterId] = dynamicActions;

          return res;
        },
        {} as AdcmClustersDynamicActionsState['clusterDynamicActions'],
      );
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

interface OpenClusterDynamicActionPayload {
  cluster: AdcmCluster;
  actionId: number;
}

const openClusterDynamicActionDialog = createAsyncThunk(
  'adcm/clustersDynamicActions/openClusterDynamicActionDialog',
  async ({ cluster, actionId }: OpenClusterDynamicActionPayload, thunkAPI) => {
    try {
      const actionDetails = await AdcmClustersApi.getClusterActionDetails(cluster.id, actionId);

      return actionDetails;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

const loadMappings = createAsyncThunk(
  'adcm/clustersDynamicActions/loadMappings',
  async ({ clusterId }: GetClusterMappingArg, thunkAPI) => {
    try {
      const mapping = await AdcmClusterMappingApi.getMapping(clusterId);
      const hosts = await AdcmClusterMappingApi.getMappingHosts(clusterId);
      const components = await AdcmClusterMappingApi.getMappingComponents(clusterId);
      const notAddedServices = await AdcmClusterServicesApi.getClusterServiceCandidates(clusterId);
      return { mapping, components, hosts, notAddedServices };
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getMappings = createAsyncThunk(
  'adcm/clustersDynamicActions/getMappings',
  async (arg: GetClusterMappingArg, thunkAPI) => {
    await thunkAPI.dispatch(loadMappings(arg));
  },
);

interface RunClusterDynamicActionPayload {
  cluster: AdcmCluster;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runClusterDynamicAction = createAsyncThunk(
  'adcm/clustersDynamicActions/runClusterDynamicAction',
  async ({ cluster, actionId, actionRunConfig }: RunClusterDynamicActionPayload, thunkAPI) => {
    try {
      // TODO: runClusterAction get big response with information about action, but wiki say that this should empty response
      await AdcmClustersApi.runClusterAction(cluster.id, actionId, actionRunConfig);

      thunkAPI.dispatch(showSuccess({ message: ActionStatuses.SuccessRun }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmClustersDynamicActionsState = {
  dialog: {
    actionDetails: AdcmDynamicActionDetails | null;
    cluster: AdcmCluster | null;
    mapping: AdcmMapping[];
    hosts: AdcmHostShortView[];
    components: AdcmMappingComponent[];
    notAddedServicesDictionary: NotAddedServicesDictionary;
    loadState: LoadState;
  };
  clusterDynamicActions: Record<number, AdcmDynamicAction[]>;
};

const createInitialState = (): AdcmClustersDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    cluster: null,
    mapping: [],
    hosts: [],
    components: [],
    notAddedServicesDictionary: {},
    loadState: LoadState.NotLoaded,
  },
  clusterDynamicActions: {},
});

const clustersDynamicActionsSlice = createSlice({
  name: 'adcm/clustersDynamicActions',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterDynamicActions() {
      return createInitialState();
    },
    closeClusterDynamicActionDialog(state) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      state.dialog = createInitialState().dialog;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadMappings.fulfilled, (state, action) => {
      state.dialog.mapping = action.payload.mapping;
      state.dialog.hosts = action.payload.hosts;
      state.dialog.components = action.payload.components;
      state.dialog.notAddedServicesDictionary = arrayToHash(action.payload.notAddedServices, (s) => s.id);
    });
    builder.addCase(getMappings.pending, (state) => {
      state.dialog.loadState = LoadState.Loading;
    });
    builder.addCase(getMappings.fulfilled, (state) => {
      state.dialog.loadState = LoadState.Loaded;
    });
    builder.addCase(loadClustersDynamicActions.fulfilled, (state, action) => {
      state.clusterDynamicActions = action.payload;
    });
    builder.addCase(loadClustersDynamicActions.rejected, (state) => {
      state.clusterDynamicActions = [];
    });
    builder.addCase(openClusterDynamicActionDialog.fulfilled, (state, action) => {
      state.dialog.actionDetails = action.payload;
      state.dialog.cluster = action.meta.arg.cluster;
    });
    builder.addCase(openClusterDynamicActionDialog.rejected, (state) => {
      clustersDynamicActionsSlice.caseReducers.closeClusterDynamicActionDialog(state);
    });
    builder.addCase(runClusterDynamicAction.pending, (state) => {
      clustersDynamicActionsSlice.caseReducers.closeClusterDynamicActionDialog(state);
    });
  },
});

export const { cleanupClusterDynamicActions, closeClusterDynamicActionDialog } = clustersDynamicActionsSlice.actions;
export { loadClustersDynamicActions, openClusterDynamicActionDialog, getMappings, runClusterDynamicAction };

export default clustersDynamicActionsSlice.reducer;
