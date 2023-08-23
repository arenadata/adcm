import { createSlice } from '@reduxjs/toolkit';
import { AdcmCluster } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { AdcmClustersApi, RequestError } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showInfo } from '@store/notificationsSlice';
import { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';

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

      return clustersActions.reduce((res, { clusterId, dynamicActions }) => {
        res[clusterId] = dynamicActions;

        return res;
      }, {} as AdcmClustersDynamicActionsState['clusterDynamicActions']);
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

      thunkAPI.dispatch(showInfo({ message: 'Action was running successfully' }));

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
  };
  clusterDynamicActions: Record<number, AdcmDynamicAction[]>;
};

const createInitialState = (): AdcmClustersDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    cluster: null,
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
      state.dialog = createInitialState().dialog;
    },
  },
  extraReducers: (builder) => {
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
export { loadClustersDynamicActions, openClusterDynamicActionDialog, runClusterDynamicAction };

export default clustersDynamicActionsSlice.reducer;
