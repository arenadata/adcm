import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterOverviewApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmClusterOverviewStatusService } from '@models/adcm/clusterOverview';

type AdcmClusterOverviewServicesState = {
  servicesStatuses: AdcmClusterOverviewStatusService[];
  count: number;
  allServicesCount: number;
  isLoading: boolean;
};

const getClusterAllServicesCount = createAsyncThunk(
  'adcm/cluster/overview/services/getAllServicesCount',
  async (clusterId: number, thunkAPI) => {
    try {
      const response = await AdcmClusterOverviewApi.getClusterServicesStatuses(clusterId, {
        pageNumber: 0,
        perPage: 1,
      });
      return response;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadClusterServicesStatuses = createAsyncThunk(
  'adcm/cluster/overview/services/loadStatuses',
  async (clusterId: number, thunkAPI) => {
    const {
      adcm: {
        clusterOverviewServicesTable: {
          filter: { servicesStatus },
          paginationParams,
        },
      },
    } = thunkAPI.getState();

    try {
      const response = await AdcmClusterOverviewApi.getClusterServicesStatuses(
        clusterId,
        paginationParams,
        servicesStatus,
      );
      return response;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterServicesStatuses = createAsyncThunk(
  'adcm/cluster/overview/services/getStatuses',
  async (clusterId: number, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await Promise.all([
      thunkAPI.dispatch(loadClusterServicesStatuses(clusterId)),
      thunkAPI.dispatch(getClusterAllServicesCount(clusterId)),
    ]);

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const refreshClusterServicesStatuses = createAsyncThunk(
  'adcm/cluster/overview/services/refreshStatuses',
  async (clusterId: number, thunkAPI) => {
    await Promise.all([
      thunkAPI.dispatch(loadClusterServicesStatuses(clusterId)),
      thunkAPI.dispatch(getClusterAllServicesCount(clusterId)),
    ]);
  },
);

const createInitialState = (): AdcmClusterOverviewServicesState => ({
  servicesStatuses: [],
  isLoading: false,
  count: 0,
  allServicesCount: 0,
});

const clusterOverviewServicesSlice = createSlice({
  name: 'adcm/cluster/overview/services',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClusterServicesStatuses() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterServicesStatuses.fulfilled, (state, action) => {
      state.servicesStatuses = action.payload.results;
      state.count = action.payload.count;
    });
    builder.addCase(loadClusterServicesStatuses.rejected, (state) => {
      state.servicesStatuses = [];
      state.count = 0;
    });
    builder.addCase(getClusterAllServicesCount.fulfilled, (state, action) => {
      state.allServicesCount = action.payload.count;
    });
    builder.addCase(getClusterAllServicesCount.rejected, (state) => {
      state.allServicesCount = 0;
    });
  },
});

const { setIsLoading, cleanupClusterServicesStatuses } = clusterOverviewServicesSlice.actions;
export { cleanupClusterServicesStatuses, getClusterServicesStatuses, refreshClusterServicesStatuses };
export default clusterOverviewServicesSlice.reducer;
