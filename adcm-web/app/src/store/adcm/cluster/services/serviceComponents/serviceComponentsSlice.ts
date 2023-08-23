import { AdcmClusterServiceComponentsApi, RequestError } from '@api';
import { defaultSpinnerDelay } from '@constants';
import { AdcmServiceComponent } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';

interface AdcmServiceComponentsState {
  serviceComponents: AdcmServiceComponent[];
  totalCount: number;
  isLoading: boolean;
}

interface LoadClusterServiceComponentsPayload {
  clusterId: number;
  serviceId: number;
}

const loadClusterServiceComponentsFromBackend = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/loadClusterServiceComponentsFromBackend',
  async ({ clusterId, serviceId }: LoadClusterServiceComponentsPayload, thunkAPI) => {
    const {
      adcm: {
        serviceComponentsTable: { sortParams, paginationParams },
      },
    } = thunkAPI.getState();

    try {
      const components = await AdcmClusterServiceComponentsApi.getServiceComponents(
        clusterId,
        serviceId,
        sortParams,
        paginationParams,
      );
      return components;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getServiceComponents = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/getServiceComponents',
  async (arg: LoadClusterServiceComponentsPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    thunkAPI.dispatch(loadClusterServiceComponentsFromBackend(arg));
    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const refreshServiceComponents = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/refreshServiceComponents',
  async (arg: LoadClusterServiceComponentsPayload, thunkAPI) => {
    thunkAPI.dispatch(loadClusterServiceComponentsFromBackend(arg));
  },
);

const createInitialState = (): AdcmServiceComponentsState => ({
  serviceComponents: [],
  totalCount: 0,
  isLoading: false,
});

const serviceComponentsSlice = createSlice({
  name: 'adcm/cluster/services/serviceComponents',
  initialState: createInitialState(),
  reducers: {
    setIsLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    cleanupServiceComponents: () => {
      return createInitialState();
    },
  },
  extraReducers(builder) {
    builder.addCase(loadClusterServiceComponentsFromBackend.fulfilled, (state, action) => {
      state.serviceComponents = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadClusterServiceComponentsFromBackend.rejected, (state) => {
      state.serviceComponents = [];
    });
  },
});

const { setIsLoading, cleanupServiceComponents } = serviceComponentsSlice.actions;
export {
  getServiceComponents,
  refreshServiceComponents,
  cleanupServiceComponents,
  loadClusterServiceComponentsFromBackend,
};
export default serviceComponentsSlice.reducer;
