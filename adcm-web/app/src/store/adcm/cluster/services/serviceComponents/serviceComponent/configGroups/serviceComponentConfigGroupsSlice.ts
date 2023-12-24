import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmConfigGroup } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmClusterServiceComponentConfigGroupsApi } from '@api';

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
}

const createInitialState = (): AdcmServiceComponentConfigGroupsState => ({
  clusterServiceConfigGroups: [],
  totalCount: 0,
  isLoading: true,
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
    });
    builder.addCase(loadServiceComponentConfigGroups.rejected, (state) => {
      state.clusterServiceConfigGroups = [];
      state.totalCount = 0;
    });
  },
});

const { setIsLoading, cleanupServiceComponentConfigGroups } = serviceComponentConfigGroupsSlice.actions;
export { getServiceComponentConfigGroups, cleanupServiceComponentConfigGroups, refreshServiceComponentConfigGroups };
export default serviceComponentConfigGroupsSlice.reducer;
