import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmRelatedServiceComponentsState, AdcmService, AdcmServiceStatus } from '@models/adcm';
import { AdcmServicesApi, RequestError } from '@api';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';

interface AdcmServiceState {
  service?: AdcmService;
  isLoading: boolean;
  relatedData: {
    successfulComponentsCount: number;
    totalComponentsCount: number;
  };
}

interface LoadServicePayload {
  clusterId: number;
  serviceId: number;
}

const loadService = createAsyncThunk(
  'adcm/service/loadService',
  async ({ clusterId, serviceId }: LoadServicePayload, thunkAPI) => {
    try {
      const service = await AdcmServicesApi.getService(clusterId, serviceId);
      return service;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: 'Service not found' }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getService = createAsyncThunk('adcm/service/getService', async (arg: LoadServicePayload, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadService(arg));

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,

    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const deleteService = createAsyncThunk(
  'adcm/service/deleteService',
  async ({ clusterId, serviceId }: LoadServicePayload, thunkAPI) => {
    try {
      await AdcmServicesApi.deleteService(clusterId, serviceId);

      thunkAPI.dispatch(showSuccess({ message: 'Service was deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

const getRelatedServiceComponentsStatuses = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/getServiceComponentsStatuses',
  async ({ clusterId, serviceId }: LoadServicePayload, thunkAPI) => {
    try {
      const componentsStatuses = await AdcmServicesApi.getRelatedServiceComponentsStatuses(clusterId, serviceId);
      return componentsStatuses;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmServiceState => ({
  service: undefined,
  isLoading: true,
  relatedData: {
    successfulComponentsCount: 0,
    totalComponentsCount: 0,
  },
});

const serviceSlice = createSlice({
  name: 'adcm/service',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupService() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadService.fulfilled, (state, action) => {
      state.service = action.payload;
    });
    builder.addCase(loadService.rejected, (state) => {
      state.service = undefined;
    });
    builder.addCase(getRelatedServiceComponentsStatuses.fulfilled, (state, action) => {
      state.relatedData.successfulComponentsCount = action.payload.components.filter(
        ({ status }: AdcmRelatedServiceComponentsState) => status === AdcmServiceStatus.Up,
      ).length;
      state.relatedData.totalComponentsCount = action.payload.components.length;
    });
    builder.addCase(getRelatedServiceComponentsStatuses.rejected, (state) => {
      state.relatedData.successfulComponentsCount = 0;
      state.relatedData.totalComponentsCount = 0;
    });
    builder.addCase(wsActions.create_service_concern, (state, action) => {
      const { id: serviceId, changes: newConcern } = action.payload.object;
      if (state.service?.id === serviceId && state.service.concerns.every((concern) => concern.id !== newConcern.id)) {
        state.service = {
          ...state.service,
          concerns: [...state.service.concerns, newConcern],
        };
      }
    });
    builder.addCase(wsActions.update_service, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.service?.id == id) {
        state.service = {
          ...state.service,
          ...changes,
        };
      }
    });
    builder.addCase(wsActions.delete_service_concern, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.service?.id === id) {
        state.service = {
          ...state.service,
          concerns: state.service.concerns.filter((concern) => concern.id !== changes.id),
        };
      }
    });
  },
});

const { setIsLoading, cleanupService } = serviceSlice.actions;
export { getService, cleanupService, deleteService, getRelatedServiceComponentsStatuses };
export default serviceSlice.reducer;
