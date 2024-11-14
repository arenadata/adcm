import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import type { AdcmConfigGroup } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import type { RequestError } from '@api';
import { AdcmClusterServiceComponentConfigGroupsApi } from '@api';
import { RequestState } from '@models/loadState';
import { processErrorResponse } from '@utils/responseUtils';

interface loadServiceComponentConfigGroupsPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
}

const loadServiceComponentConfigGroups = createAsyncThunk(
  'adcm/service/component/loadServiceComponentConfigGroups',
  async ({ clusterId, serviceId, componentId }: loadServiceComponentConfigGroupsPayload, thunkAPI) => {
    const {
      adcm: {
        serviceComponentConfigGroupsTable: { filter, sortParams, paginationParams },
      },
    } = thunkAPI.getState();
    try {
      return await AdcmClusterServiceComponentConfigGroupsApi.getConfigGroups(
        clusterId,
        serviceId,
        componentId,
        filter,
        sortParams,
        paginationParams,
      );
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getServiceComponentConfigGroups = createAsyncThunk(
  'adcm/service/component/getServiceComponentConfigGroups',
  async (arg: loadServiceComponentConfigGroupsPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await thunkAPI.dispatch(loadServiceComponentConfigGroups(arg));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const refreshServiceComponentConfigGroups = createAsyncThunk(
  'adcm/clusterConfigGroups/refreshServiceComponentConfigGroups',
  async (arg: loadServiceComponentConfigGroupsPayload, thunkAPI) => {
    thunkAPI.dispatch(loadServiceComponentConfigGroups(arg));
  },
);

interface AdcmServiceComponentConfigGroupsState {
  clusterServiceConfigGroups: AdcmConfigGroup[];
  totalCount: number;
  isLoading: boolean;
  accessCheckStatus: RequestState;
}

const createInitialState = (): AdcmServiceComponentConfigGroupsState => ({
  clusterServiceConfigGroups: [],
  totalCount: 0,
  isLoading: true,
  accessCheckStatus: RequestState.NotRequested,
});

const serviceComponentConfigGroupsSlice = createSlice({
  name: 'adcm/clusterConfigGroups',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupServiceComponentConfigGroups() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadServiceComponentConfigGroups.fulfilled, (state, action) => {
      state.clusterServiceConfigGroups = action.payload.results;
      state.totalCount = action.payload.count;
      state.accessCheckStatus = RequestState.Completed;
    });
    builder.addCase(loadServiceComponentConfigGroups.pending, (state) => {
      state.accessCheckStatus = RequestState.Pending;
    });
    builder.addCase(loadServiceComponentConfigGroups.rejected, (state, action) => {
      state.accessCheckStatus = processErrorResponse(action?.payload as RequestError);
      state.clusterServiceConfigGroups = [];
      state.totalCount = 0;
    });
  },
});

const { setIsLoading, cleanupServiceComponentConfigGroups } = serviceComponentConfigGroupsSlice.actions;
export { getServiceComponentConfigGroups, cleanupServiceComponentConfigGroups, refreshServiceComponentConfigGroups };
export default serviceComponentConfigGroupsSlice.reducer;
