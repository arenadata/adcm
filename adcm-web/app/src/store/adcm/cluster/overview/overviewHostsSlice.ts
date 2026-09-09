import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterOverviewApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import type { AdcmClusterOverviewStatusHost } from '@models/adcm/clusterOverview';
import { AdcmHostStatus, AdcmMaintenanceMode } from '@models/adcm';
import type { PaginationParams } from '@models/table';

type AdcmClusterOverviewHostsState = {
  hostsStatuses: AdcmClusterOverviewStatusHost[];
  count: number;
  isLoading: boolean;
  allCount: number;
  upCount: number;
  downCount: number;
  mmCount: number;
};

const countPagination: PaginationParams = {
  pageNumber: 0,
  perPage: 1,
};

const loadClusterHostsStatuses = createAsyncThunk(
  'adcm/cluster/overview/hosts/loadStatuses',
  async (clusterId: number, thunkAPI) => {
    const {
      adcm: {
        clusterOverviewHostsTable: {
          filter: { hostsStatus, maintenanceMode, name },
          paginationParams,
        },
      },
    } = thunkAPI.getState();

    try {
      const response = await AdcmClusterOverviewApi.getClusterHostsStatuses(
        clusterId,
        paginationParams,
        hostsStatus,
        maintenanceMode,
        name,
      );

      thunkAPI.dispatch(getClusterHostsCounts(clusterId));

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
  },
);

const getClusterHostsCounts = createAsyncThunk(
  'adcm/cluster/overview/hosts/getClusterHostsCounts',
  async (clusterId: number, thunkAPI) => {
    const {
      adcm: {
        clusterOverviewHostsTable: {
          filter: { name },
        },
      },
    } = thunkAPI.getState();

    try {
      const [allResponse, upResponse, downResponse, mmResponse] = await Promise.all([
        AdcmClusterOverviewApi.getClusterHostsStatuses(clusterId, countPagination, undefined, undefined, name),
        AdcmClusterOverviewApi.getClusterHostsStatuses(clusterId, countPagination, AdcmHostStatus.Up, undefined, name),
        AdcmClusterOverviewApi.getClusterHostsStatuses(
          clusterId,
          countPagination,
          AdcmHostStatus.Down,
          undefined,
          name,
        ),
        AdcmClusterOverviewApi.getClusterHostsStatuses(
          clusterId,
          countPagination,
          undefined,
          AdcmMaintenanceMode.On,
          name,
        ),
      ]);

      return {
        allCount: allResponse.count,
        upCount: upResponse.count,
        downCount: downResponse.count,
        mmCount: mmResponse.count,
      };
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmClusterOverviewHostsState => ({
  hostsStatuses: [],
  isLoading: true,
  count: 0,
  allCount: 0,
  upCount: 0,
  downCount: 0,
  mmCount: 0,
});

const clusterOverviewHostsSlice = createSlice({
  name: 'adcm/cluster/overview/hosts',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    resetCount(state) {
      state.count = 0;
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
    builder.addCase(getClusterHostsCounts.fulfilled, (state, action) => {
      state.allCount = action.payload.allCount;
      state.upCount = action.payload.upCount;
      state.downCount = action.payload.downCount;
      state.mmCount = action.payload.mmCount;
    });
    builder.addCase(getClusterHostsCounts.rejected, (state) => {
      state.allCount = 0;
      state.upCount = 0;
      state.downCount = 0;
      state.mmCount = 0;
    });
  },
});

const { setIsLoading, cleanupClusterHostsStatuses, resetCount } = clusterOverviewHostsSlice.actions;
export { cleanupClusterHostsStatuses, getClusterHostsStatuses, refreshClusterHostsStatuses, resetCount };
export default clusterOverviewHostsSlice.reducer;
