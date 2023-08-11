import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { defaultSpinnerDelay } from '@constants';
import { AdcmService } from '@models/adcm/service';
import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';

type AdcmServicesState = {
  services: AdcmService[];
  totalCount: number;
  isLoading: boolean;
};

interface LoadClusterServicesPayload {
  clusterId: number;
}

const loadClusterServiceFromBackend = createAsyncThunk(
  'adcm/services/loadClusterServiceFromBackend',
  async ({ clusterId }: LoadClusterServicesPayload, thunkAPI) => {
    const {
      adcm: {
        servicesTable: { filter, sortParams, paginationParams },
      },
    } = thunkAPI.getState();

    try {
      const services = await AdcmClusterServicesApi.getClusterServices(clusterId, filter, sortParams, paginationParams);
      return services;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getServices = createAsyncThunk('adcm/services/getServices', async (arg: LoadClusterServicesPayload, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadClusterServiceFromBackend(arg));
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshServices = createAsyncThunk(
  'adcm/services/refreshServices',
  async (arg: LoadClusterServicesPayload, thunkAPI) => {
    thunkAPI.dispatch(loadClusterServiceFromBackend(arg));
  },
);

const createInitialState = (): AdcmServicesState => ({
  services: [],
  totalCount: 0,
  isLoading: false,
});

const servicesSlice = createSlice({
  name: 'adcm/services',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupServices() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterServiceFromBackend.fulfilled, (state, action) => {
      state.services = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadClusterServiceFromBackend.rejected, (state) => {
      state.services = [];
    });
  },
});

export const { setIsLoading, cleanupServices } = servicesSlice.actions;
export { getServices, refreshServices };

export default servicesSlice.reducer;
