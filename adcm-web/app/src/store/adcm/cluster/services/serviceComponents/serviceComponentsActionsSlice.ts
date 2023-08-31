import { AdcmClusterServiceComponentsApi, RequestError } from '@api';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getServiceComponents } from './serviceComponentsSlice';
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

const toggleMaintenanceModeWithUpdate = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/serviceComponentsActions/toggleMaintenanceModeWithUpdate',
  async ({ clusterId, serviceId, componentId, maintenanceMode }: toggleMaintenanceModePayload, thunkAPI) => {
    try {
      await AdcmClusterServiceComponentsApi.toggleMaintenanceMode(clusterId, serviceId, componentId, maintenanceMode);
      await thunkAPI.dispatch(getServiceComponents({ clusterId, serviceId }));
      const maintenanceModeStatus = maintenanceMode === AdcmMaintenanceMode.Off ? 'disabled' : 'enabled';
      thunkAPI.dispatch(showInfo({ message: `The maintenance mode has been ${maintenanceModeStatus}` }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
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
    builder.addCase(toggleMaintenanceModeWithUpdate.pending, (state) => {
      AdcmServiceComponentsActionsSlice.caseReducers.closeMaintenanceModeDialog(state);
    });
  },
});

const { openMaintenanceModeDialog, closeMaintenanceModeDialog } = AdcmServiceComponentsActionsSlice.actions;
export { toggleMaintenanceModeWithUpdate, openMaintenanceModeDialog, closeMaintenanceModeDialog };
export default AdcmServiceComponentsActionsSlice.reducer;
