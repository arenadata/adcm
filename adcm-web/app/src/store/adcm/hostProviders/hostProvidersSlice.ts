import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostProvider } from '@models/adcm/hostProvider';
import { createAsyncThunk } from '@store/redux';
import { AdcmHostProvidersApi } from '@api';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';

interface AdcmHostProvidersState {
  hostProviders: AdcmHostProvider[];
  totalCount: number;
  isLoading: boolean;
}

const loadHostProviders = createAsyncThunk('adcm/hostProviders/loadHostProviders', async (arg, thunkAPI) => {
  const {
    adcm: {
      hostProvidersTable: { filter, sortParams, paginationParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmHostProvidersApi.getHostProviders(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getHostProviders = createAsyncThunk('adcm/hostProviders/getHostProviders', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadHostProviders());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshHostProviders = createAsyncThunk('adcm/hostProviders/refreshHostProviders', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadHostProviders());
});

const createInitialState = (): AdcmHostProvidersState => ({
  hostProviders: [],
  totalCount: 0,
  isLoading: false,
});

const hostProvidersSlice = createSlice({
  name: 'adcm/hostProviders',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupHostProviders() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadHostProviders.fulfilled, (state, action) => {
      state.hostProviders = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadHostProviders.rejected, (state) => {
      state.hostProviders = [];
    });
  },
});

const { setIsLoading, cleanupHostProviders } = hostProvidersSlice.actions;
export { getHostProviders, cleanupHostProviders, refreshHostProviders, setIsLoading };

export default hostProvidersSlice.reducer;
