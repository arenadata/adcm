import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterOverviewApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmClusterOverviewStatusHost } from '@models/adcm/clusterOverview';
import { AdcmHostStatus } from '@models/adcm';

type AdcmClusterOverviewServicesState = {
  hostsStatuses: AdcmClusterOverviewStatusHost[];
  count: number;
  isLoading: boolean;
  upCount: number;
  downCount: number;
};

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

      if (hostsStatus !== AdcmHostStatus.Down) {
        thunkAPI.dispatch(getClusterUpHostsCount(clusterId));
      }
      if (hostsStatus !== AdcmHostStatus.Up) {
        thunkAPI.dispatch(getClusterDownHostsCount(clusterId));
      }

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

const getClusterUpHostsCount = createAsyncThunk(
  'adcm/cluster/overview/services/getClusterUpHostsCount',
  async (clusterId: number, thunkAPI) => {
    try {
      const response = await AdcmClusterOverviewApi.getClusterHostsStatuses(
        clusterId,
        {
          pageNumber: 0,
          perPage: 1,
        },
        AdcmHostStatus.Up,
      );
      return response;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterDownHostsCount = createAsyncThunk(
  'adcm/cluster/overview/services/getClusterDownHostsCount',
  async (clusterId: number, thunkAPI) => {
    try {
      const response = await AdcmClusterOverviewApi.getClusterHostsStatuses(
        clusterId,
        {
          pageNumber: 0,
          perPage: 1,
        },
        AdcmHostStatus.Down,
      );
      return response;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmClusterOverviewServicesState => ({
  hostsStatuses: [],
  isLoading: true,
  count: 0,
  upCount: 0,
  downCount: 0,
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
    builder.addCase(getClusterUpHostsCount.fulfilled, (state, action) => {
      state.upCount = action.payload.count;
    });
    builder.addCase(getClusterUpHostsCount.rejected, (state) => {
      state.upCount = 0;
    });
    builder.addCase(getClusterDownHostsCount.fulfilled, (state, action) => {
      state.downCount = action.payload.count;
    });
    builder.addCase(getClusterDownHostsCount.rejected, (state) => {
      state.downCount = 0;
    });
  },
});

const { setIsLoading, cleanupClusterHostsStatuses, resetCount } = clusterOverviewHostsSlice.actions;
export { cleanupClusterHostsStatuses, getClusterHostsStatuses, refreshClusterHostsStatuses, resetCount };
export default clusterOverviewHostsSlice.reducer;
