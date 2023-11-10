import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { RequestError } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showInfo } from '@store/notificationsSlice';
import { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmClusterHostsApi } from '@api';
import { AdcmCluster, AdcmClusterHost } from '@models/adcm';
import { ActionStatuses } from '@constants';

interface LoadClusterHostsDynamicActionsPayload {
  clusterId: number;
  hosts: AdcmClusterHost[];
}

const loadClusterHostsDynamicActions = createAsyncThunk(
  'adcm/cluster/hosts/hostsDynamicActions/LoadClusterHostsDynamicActions',
  async ({ clusterId, hosts }: LoadClusterHostsDynamicActionsPayload, thunkAPI) => {
    try {
      const actionsPromises = await Promise.allSettled(
        hosts.map(async ({ id: hostId }) => ({
          hostId,
          dynamicActions: await AdcmClusterHostsApi.getClusterHostOwnActions(clusterId, hostId),
        })),
      );
      const clusterHostsActions = fulfilledFilter(actionsPromises);
      if (clusterHostsActions.length === 0 && hosts.length > 0) {
        throw new Error('All hosts cannot get those actions');
      }

      if (clusterHostsActions.length < hosts.length) {
        throw new Error('Some hosts cannot get those actions');
      }

      return clusterHostsActions.reduce((res, { hostId, dynamicActions }) => {
        res[hostId] = dynamicActions;

        return res;
      }, {} as AdcmClusterHostsDynamicActionsState['clusterHostDynamicActions']);
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

interface OpenClusterHostDynamicActionPayload {
  cluster: AdcmCluster;
  host: AdcmClusterHost;
  actionId: number;
}

const openClusterHostDynamicActionDialog = createAsyncThunk(
  'adcm/cluster/hosts/hostsDynamicActions/openClusterHostDynamicActionDialog',
  async ({ cluster, host, actionId }: OpenClusterHostDynamicActionPayload, thunkAPI) => {
    try {
      const actionDetails = await AdcmClusterHostsApi.getClusterHostActionsDetails(cluster.id, host.id, actionId);

      return actionDetails;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

interface RunClusterHostActionPayload {
  cluster: AdcmCluster;
  clusterHost: AdcmClusterHost;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runClusterHostDynamicAction = createAsyncThunk(
  'adcm/cluster/hosts/hostsDynamicActions/runClusterHostDynamicAction',
  async ({ cluster, clusterHost, actionId, actionRunConfig }: RunClusterHostActionPayload, thunkAPI) => {
    try {
      // TODO: run***Action get big response with information about action, but wiki say that this should empty response
      await AdcmClusterHostsApi.runClusterHostAction(cluster.id, clusterHost.id, actionId, actionRunConfig);

      thunkAPI.dispatch(showInfo({ message: ActionStatuses.Launched }));

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
      state.dialog.clusterHost = action.meta.arg.host;
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

export const { cleanupClusterHostDynamicActions, closeClusterHostDynamicActionDialog } =
  clusterHostsDynamicActionsSlice.actions;
export { loadClusterHostsDynamicActions, openClusterHostDynamicActionDialog, runClusterHostDynamicAction };

export default clusterHostsDynamicActionsSlice.reducer;
