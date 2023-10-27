import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { getServices } from '@store/adcm/cluster/services/servicesSlice';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { RequestError } from '@api';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { AdcmMaintenanceMode, AdcmService, AdcmServicePrototype } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { clearSolvedDependencies } from '@utils/dependsOnUtils';

interface AddClusterServicePayload {
  clusterId: number;
  servicesIds: number[];
}

interface DeleteClusterServicePayload {
  clusterId: number;
  serviceId: number;
}

interface toggleMaintenanceModePayload {
  serviceId: number;
  clusterId: number;
  maintenanceMode: AdcmMaintenanceMode;
}

const addService = createAsyncThunk(
  'adcm/servicesActions/addService',
  async ({ clusterId, servicesIds }: AddClusterServicePayload, thunkAPI) => {
    thunkAPI.dispatch(setIsAddingServices(true));
    try {
      await AdcmClusterServicesApi.addClusterService(clusterId, servicesIds);
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

const getServiceCandidates = createAsyncThunk(
  'adcm/servicesActions/getServiceCandidates',
  async (clusterId: number, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsServiceCandidatesLoading(true));

    try {
      return await AdcmClusterServicesApi.getClusterServiceCandidates(clusterId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      executeWithMinDelay({
        startDate,
        delay: defaultSpinnerDelay,
        callback: () => {
          thunkAPI.dispatch(setIsServiceCandidatesLoading(false));
        },
      });
    }
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
  maintenanceModeDialog: {
    service: AdcmService | null;
  };
  isAddingServices: boolean;
  addServicesDialog: {
    isOpen: boolean;
  };
  deleteDialog: {
    serviceId: number | null;
  };
  relatedData: {
    serviceCandidates: AdcmServicePrototype[];
    isServiceCandidatesLoading: boolean;
  };
}

const createInitialState = (): AdcmClusterServicesActionsState => ({
  maintenanceModeDialog: {
    service: null,
  },
  addServicesDialog: {
    isOpen: false,
  },
  isAddingServices: false,
  deleteDialog: {
    serviceId: null,
  },
  relatedData: {
    serviceCandidates: [],
    isServiceCandidatesLoading: false,
  },
});

const servicesActionsSlice = createSlice({
  name: 'adcm/servicesActions',
  initialState: createInitialState(),
  reducers: {
    cleanupServicesActions() {
      return createInitialState();
    },
    openAddServicesDialog(state) {
      state.addServicesDialog.isOpen = true;
    },
    closeAddServicesDialog(state) {
      state.addServicesDialog.isOpen = false;
    },
    openDeleteDialog(state, action) {
      state.deleteDialog.serviceId = action.payload;
    },
    setIsServiceCandidatesLoading(state, action) {
      state.relatedData.isServiceCandidatesLoading = action.payload;
    },
    closeDeleteDialog(state) {
      state.deleteDialog.serviceId = null;
    },
    setIsAddingServices(state, action) {
      state.isAddingServices = action.payload;
    },
    openMaintenanceModeDialog(state, action) {
      state.maintenanceModeDialog.service = action.payload;
    },
    closeMaintenanceModeDialog(state) {
      state.maintenanceModeDialog.service = null;
    },
  },
  extraReducers(builder) {
    builder.addCase(getServiceCandidates.fulfilled, (state, action) => {
      // remove dependencies to earlier added services
      state.relatedData.serviceCandidates = clearSolvedDependencies(action.payload);
    });
    builder.addCase(getServiceCandidates.rejected, (state) => {
      state.relatedData.serviceCandidates = [];
    });
    builder.addCase(toggleMaintenanceModeWithUpdate.pending, (state) => {
      servicesActionsSlice.caseReducers.closeMaintenanceModeDialog(state);
    });
  },
});

const {
  openAddServicesDialog,
  closeAddServicesDialog,
  openDeleteDialog,
  closeDeleteDialog,
  cleanupServicesActions,
  setIsAddingServices,
  openMaintenanceModeDialog,
  closeMaintenanceModeDialog,
  setIsServiceCandidatesLoading,
} = servicesActionsSlice.actions;

export {
  addService,
  deleteService,
  getServiceCandidates,
  toggleMaintenanceModeWithUpdate,
  openAddServicesDialog,
  closeAddServicesDialog,
  openDeleteDialog,
  closeDeleteDialog,
  openMaintenanceModeDialog,
  closeMaintenanceModeDialog,
};

export default servicesActionsSlice.reducer;
