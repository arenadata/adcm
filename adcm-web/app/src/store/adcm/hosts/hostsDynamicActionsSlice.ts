import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { AdcmHostsApi } from '@api';
import { arePromisesResolved, fulfilledFilter } from '@utils/promiseUtils';
import { showError, showSuccess } from '@store/notificationsSlice';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import type { AdcmHost } from '@models/adcm';
import { ActionStatuses } from '@constants';
import { setSelectedItemsIds } from '@store/adcm/hosts/hostsActionsSlice';

const loadHostsDynamicActions = createAsyncThunk(
  'adcm/hostsDynamicActions/loadHostsDynamicActions',
  async (hosts: AdcmHost[], thunkAPI) => {
    try {
      const actionsPromises = await Promise.allSettled(
        hosts.map(async ({ id: hostId }) => ({
          hostId,
          dynamicActions: await AdcmHostsApi.getHostActions(hostId),
        })),
      );
      const hostsActions = fulfilledFilter(actionsPromises);
      if (hostsActions.length === 0 && hosts.length > 0) {
        throw new Error('All hosts cannot get those actions');
      }

      if (hostsActions.length < hosts.length) {
        throw new Error('Some hosts cannot get those actions');
      }

      return hostsActions.reduce(
        (res, { hostId, dynamicActions }) => {
          res[hostId] = dynamicActions;

          return res;
        },
        {} as AdcmHostsDynamicActionsState['hostDynamicActions'],
      );
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

interface OpenHostDynamicActionPayload {
  host: AdcmHost;
  actionId: number;
}

interface OpenBulkHostDynamicActionPayload {
  hosts: AdcmHost[];
  actionName: string;
  actionIdsByHostId: Record<number, number>;
}

const openHostDynamicActionDialog = createAsyncThunk(
  'adcm/hostsDynamicActions/openHostDynamicActionDialog',
  async ({ host, actionId }: OpenHostDynamicActionPayload, thunkAPI) => {
    try {
      const actionDetails = await AdcmHostsApi.getHostActionsDetails(host.id, actionId);

      return actionDetails;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

const openBulkHostDynamicActionDialog = createAsyncThunk(
  'adcm/hostsDynamicActions/openBulkHostDynamicActionDialog',
  async ({ hosts, actionIdsByHostId, actionName }: OpenBulkHostDynamicActionPayload, thunkAPI) => {
    try {
      const firstHost = hosts[0];
      const actionId = actionIdsByHostId[firstHost.id];
      const actionDetails = await AdcmHostsApi.getHostActionsDetails(firstHost.id, actionId);

      return { actionDetails, hosts, actionIdsByHostId, actionName };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

interface RunBulkHostActionPayload {
  hosts: AdcmHost[];
  actionIdsByHostId: Record<number, number>;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runBulkHostDynamicAction = createAsyncThunk(
  'adcm/hostsDynamicActions/runBulkHostDynamicAction',
  async ({ hosts, actionIdsByHostId, actionRunConfig }: RunBulkHostActionPayload, thunkAPI) => {
    try {
      arePromisesResolved(
        await Promise.allSettled(
          hosts.map((host) => AdcmHostsApi.runHostAction(host.id, actionIdsByHostId[host.id], actionRunConfig)),
        ),
      );

      thunkAPI.dispatch(showSuccess({ message: ActionStatuses.SuccessRun }));
      thunkAPI.dispatch(setSelectedItemsIds([]));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmHostsDynamicActionsState = {
  dialog: {
    actionDetails: AdcmDynamicActionDetails | null;
    host: AdcmHost | null;
    hosts: AdcmHost[];
    actionIdsByHostId: Record<number, number>;
  };
  hostDynamicActions: Record<number, AdcmDynamicAction[]>;
};

const createInitialState = (): AdcmHostsDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    host: null,
    hosts: [],
    actionIdsByHostId: {},
  },
  hostDynamicActions: {},
});

const hostsDynamicActionsSlice = createSlice({
  name: 'adcm/hostsDynamicActionsSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupHostDynamicActions() {
      return createInitialState();
    },
    closeHostDynamicActionDialog(state) {
      // @ts-ignore
      state.dialog = createInitialState().dialog;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadHostsDynamicActions.fulfilled, (state, action) => {
      state.hostDynamicActions = action.payload;
    });
    builder.addCase(loadHostsDynamicActions.rejected, (state) => {
      state.hostDynamicActions = [];
    });
    builder.addCase(openHostDynamicActionDialog.fulfilled, (state, action) => {
      state.dialog.actionDetails = action.payload;
      state.dialog.host = action.meta.arg.host;
      state.dialog.hosts = [];
      state.dialog.actionIdsByHostId = {};
    });
    builder.addCase(openBulkHostDynamicActionDialog.fulfilled, (state, action) => {
      state.dialog.actionDetails = action.payload.actionDetails;
      state.dialog.host = action.payload.hosts[0];
      state.dialog.hosts = action.payload.hosts;
      state.dialog.actionIdsByHostId = action.payload.actionIdsByHostId;
    });
    builder.addCase(openHostDynamicActionDialog.rejected, (state) => {
      hostsDynamicActionsSlice.caseReducers.closeHostDynamicActionDialog(state);
    });
    builder.addCase(openBulkHostDynamicActionDialog.rejected, (state) => {
      hostsDynamicActionsSlice.caseReducers.closeHostDynamicActionDialog(state);
    });
    builder.addCase(runBulkHostDynamicAction.pending, (state) => {
      hostsDynamicActionsSlice.caseReducers.closeHostDynamicActionDialog(state);
    });
  },
});

export const { cleanupHostDynamicActions, closeHostDynamicActionDialog } = hostsDynamicActionsSlice.actions;
export {
  loadHostsDynamicActions,
  openHostDynamicActionDialog,
  openBulkHostDynamicActionDialog,
  runBulkHostDynamicAction,
};

export default hostsDynamicActionsSlice.reducer;
