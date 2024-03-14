import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmHostsApi, RequestError } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showSuccess } from '@store/notificationsSlice';
import { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmHost } from '@models/adcm';
import { ActionStatuses } from '@constants';

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

interface RunHostActionPayload {
  host: AdcmHost;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runHostDynamicAction = createAsyncThunk(
  'adcm/hostsDynamicActions/runHostDynamicAction',
  async ({ host, actionId, actionRunConfig }: RunHostActionPayload, thunkAPI) => {
    try {
      // TODO: run***Action get big response with information about action, but wiki say that this should empty response
      await AdcmHostsApi.runHostAction(host.id, actionId, actionRunConfig);

      thunkAPI.dispatch(showSuccess({ message: ActionStatuses.SuccessRun }));

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
  };
  hostDynamicActions: Record<number, AdcmDynamicAction[]>;
};

const createInitialState = (): AdcmHostsDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    host: null,
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
    });
    builder.addCase(openHostDynamicActionDialog.rejected, (state) => {
      hostsDynamicActionsSlice.caseReducers.closeHostDynamicActionDialog(state);
    });
    builder.addCase(runHostDynamicAction.pending, (state) => {
      hostsDynamicActionsSlice.caseReducers.closeHostDynamicActionDialog(state);
    });
  },
});

export const { cleanupHostDynamicActions, closeHostDynamicActionDialog } = hostsDynamicActionsSlice.actions;
export { loadHostsDynamicActions, openHostDynamicActionDialog, runHostDynamicAction };

export default hostsDynamicActionsSlice.reducer;
