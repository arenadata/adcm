import { AdcmClusterServiceComponentsApi, RequestError } from '@api';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { loadClusterServiceComponentFromBackend } from './serviceComponentSlice';

interface AdcmServiceComponentActionsState {
  maintenanceModeDialog: {
    id: number | null;
  };
}

interface toggleMaintenanceModePayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
  maintenanceMode: string;
}

const toggleMaintenanceModeWithUpdate = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/serviceComponent/serviceComponentActions/toggleMaintenanceModeWithUpdate',
  async ({ clusterId, serviceId, componentId, maintenanceMode }: toggleMaintenanceModePayload, thunkAPI) => {
    try {
      await AdcmClusterServiceComponentsApi.toggleMaintenanceMode(clusterId, serviceId, componentId, maintenanceMode);
      await thunkAPI.dispatch(loadClusterServiceComponentFromBackend({ clusterId, serviceId, componentId }));
      const maintenanceModeStatus = maintenanceMode === 'off' ? 'disabled' : 'enabled';
      thunkAPI.dispatch(showInfo({ message: `The maintenance mode has been ${maintenanceModeStatus}` }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    }
  },
);

const createInitialState = (): AdcmServiceComponentActionsState => ({
  maintenanceModeDialog: {
    id: null,
  },
});

const AdcmServiceComponentsActionsSlice = createSlice({
  name: 'adcm/cluster/services/serviceComponents/serviceComponent/serviceComponentActions',
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
    builder.addCase(toggleMaintenanceModeWithUpdate.pending, (state) => {
      AdcmServiceComponentsActionsSlice.caseReducers.closeMaintenanceModeDialog(state);
    });
  },
});

const { openMaintenanceModeDialog, closeMaintenanceModeDialog } = AdcmServiceComponentsActionsSlice.actions;
export { toggleMaintenanceModeWithUpdate, openMaintenanceModeDialog, closeMaintenanceModeDialog };
export default AdcmServiceComponentsActionsSlice.reducer;
