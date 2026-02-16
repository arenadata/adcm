import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { AdcmClusterHostsApi } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showSuccess } from '@store/notificationsSlice';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import type { AdcmCluster, AdcmClusterHost } from '@models/adcm';
import { ActionStatuses } from '@constants';

interface LoadClusterHostsDynamicActionsPayload {
  clusterId: number;
  hosts: AdcmClusterHost[];
}

const loadClusterHostsDynamicActions = createAsyncThunk(
  'adcm/cluster/hosts/hostsDynamicActions/LoadClusterHostsDynamicActions',
  async ({ clusterId, hosts }: LoadClusterHostsDynamicActionsPayload, thunkAPI) => {
    const {
      adcm: {
        cluster: { cluster },
      },
    } = thunkAPI.getState();

    try {
      const hostsActionsPromises = hosts.map(async ({ id: hostId }) => {
        const ownActions = await AdcmClusterHostsApi.getClusterHostOwnActions(clusterId, hostId);

        return {
          hostId,
          dynamicActions: cluster
            ? [
                ...ownActions,
                ...(await AdcmClusterHostsApi.getClusterHostPrototypeActions(clusterId, hostId, cluster.prototype.id)),
              ]
            : ownActions,
        };
      });

      const hostsActionsResults = await Promise.allSettled(hostsActionsPromises);

      const fulfilledHostsActions = fulfilledFilter(hostsActionsResults);

      if (fulfilledHostsActions.length === 0 && hosts.length > 0) {
        throw new Error('All hosts cannot get those actions');
      }

      if (fulfilledHostsActions.length < hosts.length) {
        throw new Error('Some hosts cannot get those actions');
      }

      return fulfilledHostsActions.reduce(
        (res, { hostId, dynamicActions }) => {
          res[hostId] = dynamicActions;
          return res;
        },
        {} as AdcmClusterHostsDynamicActionsState['clusterHostDynamicActions'],
      );
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

interface AdcmCreateProcessPayload {
  clusterId: number;
  hostId: number;
  actionId: number;
}

const createClusterHostDynamicActionProcess = createAsyncThunk(
  'adcm/cluster/hosts/hostsDynamicActions/createClusterHostDynamicActionProcess',
  async ({ clusterId, hostId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    const {
      adcm: {
        clusterHostsDynamicActions: {
          dialog: { clusterHost, cluster },
        },
      },
    } = thunkAPI.getState();

    try {
      const process = await AdcmClusterHostsApi.createHostActionWizardProcess(clusterId, hostId, actionId);

      if (cluster && clusterHost) {
        await thunkAPI.dispatch(openClusterHostDynamicActionDialog({ cluster, clusterHost, actionId }));
      }

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface OpenClusterHostDynamicActionPayload {
  cluster: AdcmCluster;
  clusterHost: AdcmClusterHost;
  actionId: number;
}

const openClusterHostDynamicActionDialog = createAsyncThunk(
  'adcm/cluster/hosts/hostsDynamicActions/openClusterHostDynamicActionDialog',
  async ({ cluster, clusterHost, actionId }: OpenClusterHostDynamicActionPayload, thunkAPI) => {
    try {
      const actionDetails = await AdcmClusterHostsApi.getClusterHostActionsDetails(
        cluster.id,
        clusterHost.id,
        actionId,
      );

      return actionDetails;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

export interface RunClusterHostDynamicActionPayload {
  clusterId: number;
  hostId: number;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runClusterHostDynamicAction = createAsyncThunk(
  'adcm/cluster/hosts/hostsDynamicActions/runClusterHostDynamicAction',
  async ({ clusterId, hostId, actionId, actionRunConfig }: RunClusterHostDynamicActionPayload, thunkAPI) => {
    try {
      // TODO: run***Action get big response with information about action, but wiki say that this should empty response
      await AdcmClusterHostsApi.runClusterHostAction(clusterId, hostId, actionId, actionRunConfig);

      thunkAPI.dispatch(showSuccess({ message: ActionStatuses.SuccessRun }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmClusterHostsDynamicActionsState = {
  dialog: {
    actionDetails: AdcmDynamicActionDetails | null;
    clusterHost: AdcmClusterHost | null;
    cluster: AdcmCluster | null;
  };
  clusterHostDynamicActions: Record<number, AdcmDynamicAction[]>;
};

const createInitialState = (): AdcmClusterHostsDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    clusterHost: null,
    cluster: null,
  },
  clusterHostDynamicActions: {},
});

const clusterHostsDynamicActionsSlice = createSlice({
  name: 'adcm/cluster/hosts/hostsDynamicActionsSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterHostDynamicActions() {
      return createInitialState();
    },
    cleanupClusterHostActionDetails(state) {
      // @ts-ignore
      state.dialog.actionDetails = createInitialState().dialog.actionDetails;
    },
    closeClusterHostDynamicActionDialog(state) {
      state.dialog = createInitialState().dialog;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterHostsDynamicActions.fulfilled, (state, action) => {
      state.clusterHostDynamicActions = action.payload;
    });
    builder.addCase(loadClusterHostsDynamicActions.rejected, (state) => {
      state.clusterHostDynamicActions = [];
    });
    builder.addCase(openClusterHostDynamicActionDialog.fulfilled, (state, action) => {
      state.dialog.actionDetails = action.payload;
      state.dialog.clusterHost = action.meta.arg.clusterHost;
      state.dialog.cluster = action.meta.arg.cluster;
    });
    builder.addCase(openClusterHostDynamicActionDialog.rejected, (state) => {
      clusterHostsDynamicActionsSlice.caseReducers.closeClusterHostDynamicActionDialog(state);
    });
    builder.addCase(runClusterHostDynamicAction.pending, (state) => {
      clusterHostsDynamicActionsSlice.caseReducers.closeClusterHostDynamicActionDialog(state);
    });
  },
});

export const {
  cleanupClusterHostDynamicActions,
  cleanupClusterHostActionDetails,
  closeClusterHostDynamicActionDialog,
} = clusterHostsDynamicActionsSlice.actions;
export {
  loadClusterHostsDynamicActions,
  openClusterHostDynamicActionDialog,
  runClusterHostDynamicAction,
  createClusterHostDynamicActionProcess,
};

export default clusterHostsDynamicActionsSlice.reducer;
