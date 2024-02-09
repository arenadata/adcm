import { AdcmClusterServiceComponentsApi, RequestError } from '@api';
import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmMaintenanceMode } from '@models/adcm';

interface AdcmServiceComponentsActionsState {
  maintenanceModeDialog: {
    id: number | null;
  };
}

interface toggleMaintenanceModePayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
  maintenanceMode: AdcmMaintenanceMode;
}

const toggleMaintenanceMode = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/serviceComponentsActions/toggleMaintenanceMode',
  async ({ clusterId, serviceId, componentId, maintenanceMode }: toggleMaintenanceModePayload, thunkAPI) => {
    try {
      const data = await AdcmClusterServiceComponentsApi.toggleMaintenanceMode(
        clusterId,
        serviceId,
        componentId,
        maintenanceMode,
      );
      const maintenanceModeStatus = maintenanceMode === AdcmMaintenanceMode.Off ? 'disabled' : 'enabled';
      thunkAPI.dispatch(showInfo({ message: `The maintenance mode has been ${maintenanceModeStatus}` }));
      return data;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmServiceComponentsActionsState => ({
  maintenanceModeDialog: {
    id: null,
  },
});

const AdcmServiceComponentsActionsSlice = createSlice({
  name: 'adcm/cluster/services/serviceComponents/serviceComponentsActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    openMaintenanceModeDialog(state, action) {
      state.maintenanceModeDialog.id = action.payload;
    },
    closeMaintenanceModeDialog(state) {
      state.maintenanceModeDialog.id = null;
    },
  },
  extraReducers(builder) {
    builder.addCase(toggleMaintenanceMode.pending, (state) => {
      AdcmServiceComponentsActionsSlice.caseReducers.closeMaintenanceModeDialog(state);
    });
  },
});

const { openMaintenanceModeDialog, closeMaintenanceModeDialog } = AdcmServiceComponentsActionsSlice.actions;
export { toggleMaintenanceMode, openMaintenanceModeDialog, closeMaintenanceModeDialog };
export default AdcmServiceComponentsActionsSlice.reducer;
