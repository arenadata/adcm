import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmService } from '@models/adcm';
import { AdcmServicesApi, RequestError } from '@api';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

interface AdcmServiceState {
  service?: AdcmService;
  isLoading: boolean;
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
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getService = createAsyncThunk('adcm/service/getService', async (arg: LoadServicePayload, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadService(arg));
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

      thunkAPI.dispatch(showInfo({ message: 'Service was deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

const createInitialState = (): AdcmServiceState => ({
  service: undefined,
  isLoading: false,
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
  },
});

const { setIsLoading, cleanupService } = serviceSlice.actions;
export { getService, cleanupService, deleteService };
export default serviceSlice.reducer;
