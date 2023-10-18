import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { getServices, setIsLoading } from '@store/adcm/cluster/services/servicesSlice';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { RequestError } from '@api';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { AdcmMaintenanceMode, AdcmService, AdcmServicePrototype } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';

interface AddClusterServicePayload {
  clusterId: number;
  serviceIds: number[];
}

interface DeleteClusterServicePayload {
  clusterId: number;
  serviceId: number;
}

interface LoadClusterServicesPayload {
  clusterId: number;
}

interface toggleMaintenanceModePayload {
  serviceId: number;
  clusterId: number;
  maintenanceMode: AdcmMaintenanceMode;
}

const openServiceAddDialog = createAsyncThunk(
  'adcm/servicesActions/openServiceAddDialog',
  async (clusterId: number, thunkAPI) => {
    try {
      thunkAPI.dispatch(getServicePrototypes({ clusterId }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const addService = createAsyncThunk(
  'adcm/servicesActions/addService',
  async ({ clusterId, serviceIds }: AddClusterServicePayload, thunkAPI) => {
    thunkAPI.dispatch(setIsCreating(true));
    try {
      await AdcmClusterServicesApi.addClusterService(clusterId, serviceIds);
      thunkAPI.dispatch(showInfo({ message: 'Service was added' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    } finally {
      thunkAPI.dispatch(cleanupServicesActions());
      thunkAPI.dispatch(getServices({ clusterId }));
    }
  },
);

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

const getServicePrototypesFromBackend = createAsyncThunk(
  'adcm/servicesActions/getServicePrototypesFromBackend',
  async ({ clusterId }: LoadClusterServicesPayload, thunkAPI) => {
    try {
      const servicePrototypes = await AdcmClusterServicesApi.getClusterServicePrototypes(clusterId);
      return servicePrototypes;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getServicePrototypes = createAsyncThunk(
  'adcm/servicesActions/getServicePrototypes',
  async (arg: LoadClusterServicesPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await thunkAPI.dispatch(getServicePrototypesFromBackend(arg));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const toggleMaintenanceModeWithUpdate = createAsyncThunk(
  'adcm/servicesActions/toggleMaintenanceModeWithUpdate',
  async ({ clusterId, serviceId, maintenanceMode }: toggleMaintenanceModePayload, thunkAPI) => {
    try {
      await AdcmClusterServicesApi.toggleMaintenanceMode(clusterId, serviceId, maintenanceMode);
      await thunkAPI.dispatch(getServices({ clusterId }));
      const maintenanceModeStatus = maintenanceMode === AdcmMaintenanceMode.Off ? 'disabled' : 'enabled';
      thunkAPI.dispatch(showInfo({ message: `The maintenance mode has been ${maintenanceModeStatus}` }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    }
  },
);

interface AdcmClusterServicesActionsState {
  isAddServiceDialogOpen: boolean;
  maintenanceModeDialog: {
    service: AdcmService | null;
  };
  isCreating: boolean;
  deleteDialog: {
    serviceId: number | null;
  };
  relatedData: {
    servicePrototypes: AdcmServicePrototype[];
  };
}

const createInitialState = (): AdcmClusterServicesActionsState => ({
  isAddServiceDialogOpen: false,
  maintenanceModeDialog: {
    service: null,
  },
  isCreating: false,
  deleteDialog: {
    serviceId: null,
  },
  relatedData: {
    servicePrototypes: [],
  },
});

const servicesActionsSlice = createSlice({
  name: 'adcm/servicesActions',
  initialState: createInitialState(),
  reducers: {
    cleanupServicesActions() {
      return createInitialState();
    },
    closeAddDialog(state) {
      state.isAddServiceDialogOpen = false;
    },
    openDeleteDialog(state, action) {
      state.deleteDialog.serviceId = action.payload;
    },
    closeDeleteDialog(state) {
      state.deleteDialog.serviceId = null;
    },
    setIsCreating(state, action) {
      state.isCreating = action.payload;
    },
    openMaintenanceModeDialog(state, action) {
      state.maintenanceModeDialog.service = action.payload;
    },
    closeMaintenanceModeDialog(state) {
      state.maintenanceModeDialog.service = null;
    },
  },
  extraReducers(builder) {
    builder.addCase(openServiceAddDialog.fulfilled, (state) => {
      state.isAddServiceDialogOpen = true;
    });
    builder.addCase(getServicePrototypesFromBackend.fulfilled, (state, action) => {
      state.relatedData.servicePrototypes = action.payload;
    });
    builder.addCase(getServicePrototypesFromBackend.rejected, (state) => {
      state.relatedData.servicePrototypes = [];
    });
    builder.addCase(toggleMaintenanceModeWithUpdate.pending, (state) => {
      servicesActionsSlice.caseReducers.closeMaintenanceModeDialog(state);
    });
  },
});

export const {
  closeAddDialog,
  openDeleteDialog,
  closeDeleteDialog,
  cleanupServicesActions,
  setIsCreating,
  openMaintenanceModeDialog,
  closeMaintenanceModeDialog,
} = servicesActionsSlice.actions;

export { openServiceAddDialog, addService, deleteService, getServicePrototypes, toggleMaintenanceModeWithUpdate };

export default servicesActionsSlice.reducer;
