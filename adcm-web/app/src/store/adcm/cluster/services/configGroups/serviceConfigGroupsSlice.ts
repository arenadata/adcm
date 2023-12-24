import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmConfigGroup } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmClusterServiceConfigGroupsApi } from '@api';

interface loadClusterServiceConfigGroupsPayload {
  clusterId: number;
  serviceId: number;
}

const loadClusterServiceConfigGroups = createAsyncThunk(
  'adcm/cluster/services/loadClusterServiceConfigGroups',
  async ({ clusterId, serviceId }: loadClusterServiceConfigGroupsPayload, thunkAPI) => {
    const {
      adcm: {
        serviceConfigGroupsTable: { filter, sortParams, paginationParams },
      },
    } = thunkAPI.getState();
    try {
      return await AdcmClusterServiceConfigGroupsApi.getConfigGroups(
        clusterId,
        serviceId,
        filter,
        sortParams,
        paginationParams,
      );
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterServiceConfigGroups = createAsyncThunk(
  'adcm/cluster/services/getClusterServiceConfigGroups',
  async (arg: loadClusterServiceConfigGroupsPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await thunkAPI.dispatch(loadClusterServiceConfigGroups(arg));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const refreshClusterServiceConfigGroups = createAsyncThunk(
  'adcm/clusterConfigGroups/refreshClusterServiceConfigGroups',
  async (arg: loadClusterServiceConfigGroupsPayload, thunkAPI) => {
    thunkAPI.dispatch(loadClusterServiceConfigGroups(arg));
  },
);

interface AdcmClusterServiceConfigGroupsState {
  clusterServiceConfigGroups: AdcmConfigGroup[];
  totalCount: number;
  isLoading: boolean;
}

const createInitialState = (): AdcmClusterServiceConfigGroupsState => ({
  clusterServiceConfigGroups: [],
  totalCount: 0,
  isLoading: true,
});

const serviceConfigGroupsSlice = createSlice({
  name: 'adcm/clusterConfigGroups',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClusterServiceConfigGroups() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterServiceConfigGroups.fulfilled, (state, action) => {
      state.clusterServiceConfigGroups = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadClusterServiceConfigGroups.rejected, (state) => {
      state.clusterServiceConfigGroups = [];
      state.totalCount = 0;
    });
  },
});

const { setIsLoading, cleanupClusterServiceConfigGroups } = serviceConfigGroupsSlice.actions;
export { getClusterServiceConfigGroups, cleanupClusterServiceConfigGroups, refreshClusterServiceConfigGroups };
export default serviceConfigGroupsSlice.reducer;
