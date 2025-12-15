import { createSlice } from '@reduxjs/toolkit';
import type { AdcmCluster } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { AdcmClustersApi } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showSuccess } from '@store/notificationsSlice';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { ActionStatuses } from '@constants';

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

interface AdcmCreateProcessPayload {
  clusterId: number;
  actionId: number;
}

const createClusterDynamicActionProcess = createAsyncThunk(
  'adcm/clustersDynamicActions/createClusterDynamicActionProcess',
  async ({ clusterId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    const {
      adcm: {
        clustersDynamicActions: {
          dialog: { cluster },
        },
      },
    } = thunkAPI.getState();

    try {
      const process = await AdcmClustersApi.createClusterActionWizardProcess(clusterId, actionId);

      if (cluster) {
        await thunkAPI.dispatch(openClusterDynamicActionDialog({ cluster, actionId }));
      }

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
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

export interface RunClusterDynamicActionPayload {
  clusterId: number;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runClusterDynamicAction = createAsyncThunk(
  'adcm/clustersDynamicActions/runClusterDynamicAction',
  async ({ clusterId, actionId, actionRunConfig }: RunClusterDynamicActionPayload, thunkAPI) => {
    try {
      // TODO: runClusterAction get big response with information about action, but wiki say that this should empty response
      await AdcmClustersApi.runClusterAction(clusterId, actionId, actionRunConfig);

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
    cleanupClusterActionDetails(state) {
      // @ts-ignore
      state.dialog.actionDetails = createInitialState().dialog.actionDetails;
    },
    closeClusterDynamicActionDialog(state) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
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

export const { cleanupClusterDynamicActions, cleanupClusterActionDetails, closeClusterDynamicActionDialog } =
  clustersDynamicActionsSlice.actions;
export {
  loadClustersDynamicActions,
  createClusterDynamicActionProcess,
  openClusterDynamicActionDialog,
  runClusterDynamicAction,
};

export default clustersDynamicActionsSlice.reducer;
