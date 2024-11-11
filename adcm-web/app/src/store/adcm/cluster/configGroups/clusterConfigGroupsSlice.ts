import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import type { AdcmConfigGroup } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import type { RequestError } from '@api';
import { AdcmClusterConfigGroupsApi } from '@api';
import { RequestState } from '@models/loadState';
import { processErrorResponse } from '@utils/responseUtils';

const loadClusterConfigGroups = createAsyncThunk(
  'adcm/clusterConfigGroups/loadClusterConfigGroups',
  async (clusterId: number, thunkAPI) => {
    const {
      adcm: {
        clusterConfigGroupsTable: { filter, sortParams, paginationParams },
      },
    } = thunkAPI.getState();
    try {
      return await AdcmClusterConfigGroupsApi.getConfigGroups(clusterId, filter, sortParams, paginationParams);
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterConfigGroups = createAsyncThunk(
  'adcm/clusterConfigGroups/getClusterConfigGroups',
  async (clusterId: number, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await thunkAPI.dispatch(loadClusterConfigGroups(clusterId));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const refreshClusterConfigGroups = createAsyncThunk(
  'adcm/clusterConfigGroups/refreshClusterConfigGroups',
  async (clusterId: number, thunkAPI) => {
    thunkAPI.dispatch(loadClusterConfigGroups(clusterId));
  },
);

type AdcmClusterConfigGroupsState = {
  clusterConfigGroups: AdcmConfigGroup[];
  totalCount: number;
  isLoading: boolean;
  accessCheckStatus: RequestState;
};

const createInitialState = (): AdcmClusterConfigGroupsState => ({
  clusterConfigGroups: [],
  totalCount: 0,
  isLoading: true,
  accessCheckStatus: RequestState.NotRequested,
});

const clusterConfigGroupsSlice = createSlice({
  name: 'adcm/clusterConfigGroups',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClusterConfigGroups() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterConfigGroups.fulfilled, (state, action) => {
      state.clusterConfigGroups = action.payload.results;
      state.totalCount = action.payload.count;
      state.accessCheckStatus = RequestState.Completed;
    });
    builder.addCase(loadClusterConfigGroups.pending, (state) => {
      state.accessCheckStatus = RequestState.Pending;
    });
    builder.addCase(loadClusterConfigGroups.rejected, (state, action) => {
      state.accessCheckStatus = processErrorResponse(action?.payload as RequestError);
      state.clusterConfigGroups = [];
      state.totalCount = 0;
    });
  },
});

const { setIsLoading, cleanupClusterConfigGroups } = clusterConfigGroupsSlice.actions;
export { getClusterConfigGroups, cleanupClusterConfigGroups, refreshClusterConfigGroups };
export default clusterConfigGroupsSlice.reducer;
