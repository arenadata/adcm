import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { AdcmHostProvidersApi } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showSuccess } from '@store/notificationsSlice';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import type { AdcmHostProvider } from '@models/adcm';
import { ActionStatuses } from '@constants';

const loadHostProvidersDynamicActions = createAsyncThunk(
  'adcm/hostProvidersDynamicActions/loadHostProvidersDynamicActions',
  async (hostProviders: AdcmHostProvider[], thunkAPI) => {
    try {
      const actionsPromises = await Promise.allSettled(
        hostProviders.map(async ({ id }) => ({
          id,
          dynamicActions: await AdcmHostProvidersApi.getHostProviderActions(id),
        })),
      );
      const hostProvidersActions = fulfilledFilter(actionsPromises);
      if (hostProvidersActions.length === 0 && hostProviders.length > 0) {
        throw new Error('All hosts providers cannot get those actions');
      }

      if (hostProvidersActions.length < hostProviders.length) {
        throw new Error('Some host providers cannot get those actions');
      }

      return hostProvidersActions.reduce(
        (res, { id, dynamicActions }) => {
          res[id] = dynamicActions;

          return res;
        },
        {} as AdcmHostProvidersDynamicActionsState['hostProviderDynamicActions'],
      );
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

interface OpenHostProviderDynamicActionPayload {
  hostProvider: AdcmHostProvider;
  actionId: number;
}

const openHostProviderDynamicActionDialog = createAsyncThunk(
  'adcm/hostProvidersDynamicActions/openHostProviderDynamicActionDialog',
  async ({ hostProvider, actionId }: OpenHostProviderDynamicActionPayload, thunkAPI) => {
    try {
      const actionDetails = await AdcmHostProvidersApi.getHostProviderActionsDetails(hostProvider.id, actionId);
      return actionDetails;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

interface RunHostProviderActionPayload {
  hostProvider: AdcmHostProvider;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runHostProviderDynamicAction = createAsyncThunk(
  'adcm/hostProvidersDynamicActions/runHostProviderDynamicAction',
  async ({ hostProvider, actionId, actionRunConfig }: RunHostProviderActionPayload, thunkAPI) => {
    try {
      // TODO: run***Action get big response with information about action, but wiki say that this should empty response
      await AdcmHostProvidersApi.runHostProviderAction(hostProvider.id, actionId, actionRunConfig);

      thunkAPI.dispatch(showSuccess({ message: ActionStatuses.SuccessRun }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmHostProvidersDynamicActionsState = {
  dialog: {
    actionDetails: AdcmDynamicActionDetails | null;
    hostProvider: AdcmHostProvider | null;
  };
  hostProviderDynamicActions: Record<number, AdcmDynamicAction[]>;
};

const createInitialState = (): AdcmHostProvidersDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    hostProvider: null,
  },
  hostProviderDynamicActions: {},
});

const hostProvidersDynamicActionsSlice = createSlice({
  name: 'adcm/hostProvidersDynamicActionsSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupHostProviderDynamicActions() {
      return createInitialState();
    },
    closeHostProviderDynamicActionDialog(state) {
      state.dialog = createInitialState().dialog;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadHostProvidersDynamicActions.fulfilled, (state, action) => {
      state.hostProviderDynamicActions = action.payload;
    });
    builder.addCase(loadHostProvidersDynamicActions.rejected, (state) => {
      state.hostProviderDynamicActions = [];
    });
    builder.addCase(openHostProviderDynamicActionDialog.fulfilled, (state, action) => {
      state.dialog.actionDetails = action.payload;
      state.dialog.hostProvider = action.meta.arg.hostProvider;
    });
    builder.addCase(openHostProviderDynamicActionDialog.rejected, (state) => {
      hostProvidersDynamicActionsSlice.caseReducers.closeHostProviderDynamicActionDialog(state);
    });
    builder.addCase(runHostProviderDynamicAction.pending, (state) => {
      hostProvidersDynamicActionsSlice.caseReducers.closeHostProviderDynamicActionDialog(state);
    });
  },
});

export const { cleanupHostProviderDynamicActions, closeHostProviderDynamicActionDialog } =
  hostProvidersDynamicActionsSlice.actions;
export { loadHostProvidersDynamicActions, openHostProviderDynamicActionDialog, runHostProviderDynamicAction };

export default hostProvidersDynamicActionsSlice.reducer;
