import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { getServices } from '@store/adcm/cluster/services/servicesSlice';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { RequestError } from '@api';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';

interface DeleteClusterServicePayload {
  clusterId: number;
  serviceId: number;
}

const deleteService = createAsyncThunk(
  'adcm/servicesActions/deleteService',
  async ({ clusterId, serviceId }: DeleteClusterServicePayload, thunkAPI) => {
    try {
      await AdcmClusterServicesApi.deleteClusterService(clusterId, serviceId);
      thunkAPI.dispatch(showInfo({ message: 'Service was deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    } finally {
      thunkAPI.dispatch(getServices({ clusterId }));
    }
  },
);

interface AdcmClusterServicesActionsState {
  deleteDialog: {
    serviceId: number | null;
  };
}

const createInitialState = (): AdcmClusterServicesActionsState => ({
  deleteDialog: {
    serviceId: null,
  },
});

const hostsActionsSlice = createSlice({
  name: 'adcm/servicesActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    openDeleteDialog(state, action) {
      state.deleteDialog.serviceId = action.payload;
    },
    closeDeleteDialog(state) {
      state.deleteDialog.serviceId = null;
    },
  },
});

export const { openDeleteDialog, closeDeleteDialog } = hostsActionsSlice.actions;

export { deleteService };

export default hostsActionsSlice.reducer;
