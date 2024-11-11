import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterOverviewApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import type { AdcmClusterOverviewStatusService } from '@models/adcm/clusterOverview';
import { AdcmServiceStatus } from '@models/adcm';

type AdcmClusterOverviewServicesState = {
  servicesStatuses: AdcmClusterOverviewStatusService[];
  count: number;
  isLoading: boolean;
  upCount: number;
  downCount: number;
};

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

      if (servicesStatus !== AdcmServiceStatus.Down) {
        thunkAPI.dispatch(getClusterUpServicesCount(clusterId));
      }
      if (servicesStatus !== AdcmServiceStatus.Up) {
        thunkAPI.dispatch(getClusterDownServicesCount(clusterId));
      }

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

const getClusterUpServicesCount = createAsyncThunk(
  'adcm/cluster/overview/services/getClusterUpServicesCount',
  async (clusterId: number, thunkAPI) => {
    try {
      const response = await AdcmClusterOverviewApi.getClusterServicesStatuses(
        clusterId,
        {
          pageNumber: 0,
          perPage: 1,
        },
        AdcmServiceStatus.Up,
      );
      return response;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterDownServicesCount = createAsyncThunk(
  'adcm/cluster/overview/services/getClusterDownServicesCount',
  async (clusterId: number, thunkAPI) => {
    try {
      const response = await AdcmClusterOverviewApi.getClusterServicesStatuses(
        clusterId,
        {
          pageNumber: 0,
          perPage: 1,
        },
        AdcmServiceStatus.Down,
      );
      return response;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmClusterOverviewServicesState => ({
  servicesStatuses: [],
  isLoading: true,
  count: 0,
  upCount: 0,
  downCount: 0,
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
    builder.addCase(getClusterUpServicesCount.fulfilled, (state, action) => {
      state.upCount = action.payload.count;
    });
    builder.addCase(getClusterUpServicesCount.rejected, (state) => {
      state.upCount = 0;
    });
    builder.addCase(getClusterDownServicesCount.fulfilled, (state, action) => {
      state.downCount = action.payload.count;
    });
    builder.addCase(getClusterDownServicesCount.rejected, (state) => {
      state.downCount = 0;
    });
  },
});

const { setIsLoading, cleanupClusterServicesStatuses, resetCount } = clusterOverviewServicesSlice.actions;
export { cleanupClusterServicesStatuses, getClusterServicesStatuses, refreshClusterServicesStatuses, resetCount };
export default clusterOverviewServicesSlice.reducer;
