import { AdcmHost } from '@models/adcm/host';
import { createAsyncThunk } from '@store/redux';
import { defaultSpinnerDelay } from '@constants';
import { executeWithMinDelay } from '@utils/requestUtils';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostsApi } from '@api';

type AdcmHostsState = {
  hosts: AdcmHost[];
  totalCount: number;
  isLoading: boolean;
};

const loadHosts = createAsyncThunk('adcm/hosts/loadHosts', async (arg, thunkAPI) => {
  const {
    adcm: {
      hostsTable: { filter, sortParams, paginationParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmHostsApi.getHosts(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getHosts = createAsyncThunk('adcm/hosts/getHosts', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadHosts());
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshHosts = createAsyncThunk('adcm/hosts/refreshHosts', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadHosts());
});

const createInitialState = (): AdcmHostsState => ({
  hosts: [],
  totalCount: 0,
  isLoading: false,
});

const hostsSlice = createSlice({
  name: 'adcm/hosts',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupHosts() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadHosts.fulfilled, (state, action) => {
      state.hosts = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadHosts.rejected, (state) => {
      state.hosts = [];
    });
  },
});

export const { setIsLoading, cleanupHosts } = hostsSlice.actions;
export { getHosts, refreshHosts };

export default hostsSlice.reducer;
