import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { getServices, setIsLoading } from '@store/adcm/cluster/services/servicesSlice';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { RequestError } from '@api';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { AdcmServicePrototype } from '@models/adcm';
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
    try {
      await AdcmClusterServicesApi.addClusterService(clusterId, serviceIds);
      thunkAPI.dispatch(showInfo({ message: 'Service was added' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    } finally {
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

    thunkAPI.dispatch(getServicePrototypesFromBackend(arg));
    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

interface AdcmClusterServicesActionsState {
  isAddServiceDialogOpen: boolean;
  deleteDialog: {
    serviceId: number | null;
  };
  relatedData: {
    servicePrototypes: AdcmServicePrototype[];
  };
}

const createInitialState = (): AdcmClusterServicesActionsState => ({
  isAddServiceDialogOpen: false,
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
  },
});

export const { closeAddDialog, openDeleteDialog, closeDeleteDialog, cleanupServicesActions } =
  servicesActionsSlice.actions;

export { openServiceAddDialog, addService, deleteService, getServicePrototypes };

export default servicesActionsSlice.reducer;
