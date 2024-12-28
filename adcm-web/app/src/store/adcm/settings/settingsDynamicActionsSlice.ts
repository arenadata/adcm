import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { AdcmSettingsApi } from '@api';
import { showError, showSuccess } from '@store/notificationsSlice';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { ActionStatuses } from '@constants';

const loadAdcmSettingsDynamicActions = createAsyncThunk(
  'adcm/clustersDynamicActions/loadAdcmSettingsDynamicActions',
  async (_, thunkAPI) => {
    try {
      return await AdcmSettingsApi.getAdcmSettingsActions();
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

const openAdcmSettingsDynamicActionDialog = createAsyncThunk(
  'adcm/clustersDynamicActions/openAdcmSettingsDynamicActionDialog',
  async (actionId: number, thunkAPI) => {
    try {
      const actionDetails = await AdcmSettingsApi.getAdcmSettingsActionDetails(actionId);

      return actionDetails;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

interface RunAdcmSettingsDynamicActionPayload {
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runAdcmSettingsDynamicAction = createAsyncThunk(
  'adcm/adcmSettingsDynamicActions/runAdcmSettingsDynamicAction',
  async ({ actionId, actionRunConfig }: RunAdcmSettingsDynamicActionPayload, thunkAPI) => {
    try {
      // TODO: runAdcmSettingsAction get big response with information about action, but wiki say that this should empty response
      await AdcmSettingsApi.runAdcmSettingsAction(actionId, actionRunConfig);

      thunkAPI.dispatch(showSuccess({ message: ActionStatuses.SuccessRun }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmSettingsDynamicActionsState = {
  dialog: {
    actionDetails: AdcmDynamicActionDetails | null;
    isOpen: boolean;
  };
  adcmSettingsDynamicActions: AdcmDynamicAction[];
};

const createInitialState = (): AdcmSettingsDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    isOpen: false,
  },
  adcmSettingsDynamicActions: [],
});

const adcmSettingsDynamicActionsSlice = createSlice({
  name: 'adcm/adcmSettingsDynamicActions',
  initialState: createInitialState(),
  reducers: {
    cleanupAdcmSettingsDynamicActions() {
      return createInitialState();
    },
    closeAdcmSettingsDynamicActionDialog(state) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      state.dialog = createInitialState().dialog;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadAdcmSettingsDynamicActions.fulfilled, (state, action) => {
      state.adcmSettingsDynamicActions = action.payload;
    });
    builder.addCase(loadAdcmSettingsDynamicActions.rejected, (state) => {
      state.adcmSettingsDynamicActions = [];
    });
    builder.addCase(openAdcmSettingsDynamicActionDialog.fulfilled, (state, action) => {
      state.dialog.actionDetails = action.payload;
      state.dialog.isOpen = true;
    });
    builder.addCase(openAdcmSettingsDynamicActionDialog.rejected, (state) => {
      adcmSettingsDynamicActionsSlice.caseReducers.closeAdcmSettingsDynamicActionDialog(state);
    });
    builder.addCase(runAdcmSettingsDynamicAction.pending, (state) => {
      adcmSettingsDynamicActionsSlice.caseReducers.closeAdcmSettingsDynamicActionDialog(state);
    });
  },
});

export const { cleanupAdcmSettingsDynamicActions, closeAdcmSettingsDynamicActionDialog } =
  adcmSettingsDynamicActionsSlice.actions;
export { loadAdcmSettingsDynamicActions, openAdcmSettingsDynamicActionDialog, runAdcmSettingsDynamicAction };

export default adcmSettingsDynamicActionsSlice.reducer;
