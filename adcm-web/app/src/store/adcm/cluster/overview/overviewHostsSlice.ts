import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterOverviewApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmClusterOverviewStatusHost } from '@models/adcm/clusterOverview';

type AdcmClusterOverviewServicesState = {
  hostsStatuses: AdcmClusterOverviewStatusHost[];
  count: number;
  allHostsCount: number;
  isLoading: boolean;
};

const getClusterAllHostsCount = createAsyncThunk(
  'adcm/cluster/overview/hosts/getAllHostsCount',
  async (clusterId: number, thunkAPI) => {
    try {
      const response = await AdcmClusterOverviewApi.getClusterHostsStatuses(clusterId, {
        pageNumber: 0,
        perPage: 1,
      });
      return response;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadClusterHostsStatuses = createAsyncThunk(
  'adcm/cluster/overview/hosts/loadStatuses',
  async (clusterId: number, thunkAPI) => {
    const {
      adcm: {
        clusterOverviewHostsTable: {
          filter: { hostsStatus },
          paginationParams,
        },
      },
    } = thunkAPI.getState();

    try {
      const response = await AdcmClusterOverviewApi.getClusterHostsStatuses(clusterId, paginationParams, hostsStatus);
      return response;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterHostsStatuses = createAsyncThunk(
  'adcm/cluster/overview/hosts/getStatuses',
  async (clusterId: number, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await thunkAPI.dispatch(loadClusterHostsStatuses(clusterId));
    await thunkAPI.dispatch(getClusterAllHostsCount(clusterId));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const refreshClusterHostsStatuses = createAsyncThunk(
  'adcm/cluster/overview/hosts/refreshStatuses',
  async (clusterId: number, thunkAPI) => {
    thunkAPI.dispatch(loadClusterHostsStatuses(clusterId));
    thunkAPI.dispatch(getClusterAllHostsCount(clusterId));
  },
);

const createInitialState = (): AdcmClusterOverviewServicesState => ({
  hostsStatuses: [],
  isLoading: false,
  count: 0,
  allHostsCount: 0,
});

const clusterOverviewHostsSlice = createSlice({
  name: 'adcm/cluster/overview/hosts',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClusterHostsStatuses() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterHostsStatuses.fulfilled, (state, action) => {
      state.hostsStatuses = action.payload.results;
      state.count = action.payload.count;
    });
    builder.addCase(loadClusterHostsStatuses.rejected, (state) => {
      state.hostsStatuses = [];
      state.count = 0;
    });
    builder.addCase(getClusterAllHostsCount.fulfilled, (state, action) => {
      state.allHostsCount = action.payload.count;
    });
    builder.addCase(getClusterAllHostsCount.rejected, (state) => {
      state.allHostsCount = 0;
    });
  },
});

const { setIsLoading, cleanupClusterHostsStatuses } = clusterOverviewHostsSlice.actions;
export { cleanupClusterHostsStatuses, getClusterHostsStatuses, refreshClusterHostsStatuses };
export default clusterOverviewHostsSlice.reducer;
