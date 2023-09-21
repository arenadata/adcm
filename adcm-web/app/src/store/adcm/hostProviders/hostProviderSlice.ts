import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostProvider } from '@models/adcm/hostProvider';
import { createAsyncThunk } from '@store/redux';
import { AdcmHostProvidersApi, AdcmHostsApi } from '@api';

interface AdcmHostProviderState {
  hostProvider: AdcmHostProvider | null;
  hostsCount: number;
}

const getHostsCount = createAsyncThunk('adcm/hostProvider/getHostsCount', async (hostProvider: string, thunkAPI) => {
  try {
    const batch = await AdcmHostsApi.getHosts(
      { hostProvider },
      { sortBy: '', sortDirection: 'asc' },
      { perPage: 1, pageNumber: 1 },
    );
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getHostProvider = createAsyncThunk('adcm/hostProvider/getHostProvider', async (id: number, thunkAPI) => {
  try {
    return await AdcmHostProvidersApi.getHostProvider(id);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): AdcmHostProviderState => ({
  hostProvider: null,
  hostsCount: 0,
});

const hostProviderSlice = createSlice({
  name: 'adcm/hostProvider',
  initialState: createInitialState(),
  reducers: {
    cleanupHostProvider() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getHostProvider.fulfilled, (state, action) => {
      state.hostProvider = action.payload;
    });
    builder.addCase(getHostProvider.rejected, (state) => {
      state.hostProvider = null;
    });
    builder.addCase(getHostsCount.fulfilled, (state, action) => {
      state.hostsCount = action.payload.count;
    });
  },
});

const { cleanupHostProvider } = hostProviderSlice.actions;
export { getHostProvider, getHostsCount, cleanupHostProvider };

export default hostProviderSlice.reducer;
