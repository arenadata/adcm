import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmConfigGroup } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmHostProviderConfigGroupsApi, RequestError } from '@api';
import { RequestState } from '@models/loadState';
import { processErrorResponse } from '@utils/responseUtils';

const loadHostProviderConfigGroups = createAsyncThunk(
  'adcm/hostProviderConfigGroups/loadHostProviderConfigGroups',
  async (hostProviderId: number, thunkAPI) => {
    const {
      adcm: {
        hostProviderConfigGroupsTable: { filter, sortParams, paginationParams },
      },
    } = thunkAPI.getState();
    try {
      return await AdcmHostProviderConfigGroupsApi.getConfigGroups(
        hostProviderId,
        filter,
        sortParams,
        paginationParams,
      );
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getHostProviderConfigGroups = createAsyncThunk(
  'adcm/hostProviderConfigGroups/getHostProviderConfigGroups',
  async (hostProviderId: number, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await thunkAPI.dispatch(loadHostProviderConfigGroups(hostProviderId));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const refreshHostProviderConfigGroups = createAsyncThunk(
  'adcm/hostProviderConfigGroups/refreshHostProviderConfigGroups',
  async (hostProviderId: number, thunkAPI) => {
    thunkAPI.dispatch(loadHostProviderConfigGroups(hostProviderId));
  },
);

type AdcmHostProviderConfigGroupsState = {
  hostProviderConfigGroups: AdcmConfigGroup[];
  totalCount: number;
  isLoading: boolean;
  accessCheckStatus: RequestState;
};

const createInitialState = (): AdcmHostProviderConfigGroupsState => ({
  hostProviderConfigGroups: [],
  totalCount: 0,
  isLoading: true,
  accessCheckStatus: RequestState.NotRequested,
});

const hostProviderConfigGroupsSlice = createSlice({
  name: 'adcm/hostProviderConfigGroups',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupHostProviderConfigGroups() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadHostProviderConfigGroups.fulfilled, (state, action) => {
      state.hostProviderConfigGroups = action.payload.results;
      state.totalCount = action.payload.count;
      state.accessCheckStatus = RequestState.Completed;
    });
    builder.addCase(loadHostProviderConfigGroups.pending, (state) => {
      state.accessCheckStatus = RequestState.Pending;
    });
    builder.addCase(loadHostProviderConfigGroups.rejected, (state, action) => {
      state.accessCheckStatus = processErrorResponse(action?.payload as RequestError);
      state.hostProviderConfigGroups = [];
      state.totalCount = 0;
    });
  },
});

const { setIsLoading, cleanupHostProviderConfigGroups } = hostProviderConfigGroupsSlice.actions;
export { getHostProviderConfigGroups, cleanupHostProviderConfigGroups, refreshHostProviderConfigGroups };
export default hostProviderConfigGroupsSlice.reducer;
