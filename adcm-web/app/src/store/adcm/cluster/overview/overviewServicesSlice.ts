import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterOverviewApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import type { AdcmClusterOverviewStatusService } from '@models/adcm/clusterOverview';
import { AdcmMaintenanceMode, AdcmServiceStatus } from '@models/adcm';
import type { PaginationParams } from '@models/table';

type AdcmClusterOverviewServicesState = {
  servicesStatuses: AdcmClusterOverviewStatusService[];
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

const loadClusterServicesStatuses = createAsyncThunk(
  'adcm/cluster/overview/services/loadStatuses',
  async (clusterId: number, thunkAPI) => {
    const {
      adcm: {
        clusterOverviewServicesTable: {
          filter: { servicesStatus, maintenanceMode, displayName },
          paginationParams,
        },
      },
    } = thunkAPI.getState();

    try {
      const response = await AdcmClusterOverviewApi.getClusterServicesStatuses(
        clusterId,
        paginationParams,
        servicesStatus,
        maintenanceMode,
        displayName,
      );

      thunkAPI.dispatch(getClusterServicesCounts(clusterId));

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

    await thunkAPI.dispatch(loadClusterServicesStatuses(clusterId));

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
    await thunkAPI.dispatch(loadClusterServicesStatuses(clusterId));
  },
);

const getClusterServicesCounts = createAsyncThunk(
  'adcm/cluster/overview/services/getClusterServicesCounts',
  async (clusterId: number, thunkAPI) => {
    const {
      adcm: {
        clusterOverviewServicesTable: {
          filter: { displayName },
        },
      },
    } = thunkAPI.getState();

    try {
      const [allResponse, upResponse, downResponse, mmResponse] = await Promise.all([
        AdcmClusterOverviewApi.getClusterServicesStatuses(
          clusterId,
          countPagination,
          undefined,
          undefined,
          displayName,
        ),
        AdcmClusterOverviewApi.getClusterServicesStatuses(
          clusterId,
          countPagination,
          AdcmServiceStatus.Up,
          undefined,
          displayName,
        ),
        AdcmClusterOverviewApi.getClusterServicesStatuses(
          clusterId,
          countPagination,
          AdcmServiceStatus.Down,
          undefined,
          displayName,
        ),
        AdcmClusterOverviewApi.getClusterServicesStatuses(
          clusterId,
          countPagination,
          undefined,
          AdcmMaintenanceMode.On,
          displayName,
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

const createInitialState = (): AdcmClusterOverviewServicesState => ({
  servicesStatuses: [],
  isLoading: true,
  count: 0,
  allCount: 0,
  upCount: 0,
  downCount: 0,
  mmCount: 0,
});

const clusterOverviewServicesSlice = createSlice({
  name: 'adcm/cluster/overview/services',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    resetCount(state) {
      state.count = 0;
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
    builder.addCase(getClusterServicesCounts.fulfilled, (state, action) => {
      state.allCount = action.payload.allCount;
      state.upCount = action.payload.upCount;
      state.downCount = action.payload.downCount;
      state.mmCount = action.payload.mmCount;
    });
    builder.addCase(getClusterServicesCounts.rejected, (state) => {
      state.allCount = 0;
      state.upCount = 0;
      state.downCount = 0;
      state.mmCount = 0;
    });
  },
});

const { setIsLoading, cleanupClusterServicesStatuses, resetCount } = clusterOverviewServicesSlice.actions;
export { cleanupClusterServicesStatuses, getClusterServicesStatuses, refreshClusterServicesStatuses, resetCount };
export default clusterOverviewServicesSlice.reducer;
