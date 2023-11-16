import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostProvider } from '@models/adcm/hostProvider';
import { createAsyncThunk } from '@store/redux';
import { AdcmHostProvidersApi } from '@api';
import { executeWithMinDelay } from '@utils/requestUtils';
import { updateIfExists } from '@utils/objectUtils';
import { defaultSpinnerDelay } from '@constants';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';

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
    builder.addCase(wsActions.update_provider, (state, action) => {
      const { id, changes } = action.payload.object;
      state.hostProviders = updateIfExists<AdcmHostProvider>(
        state.hostProviders,
        (hostProvider) => hostProvider.id === id,
        () => changes,
      );
    });
    builder.addCase(wsActions.create_hostprovider_concern, (state, action) => {
      const { id: hostProviderId, changes: newConcern } = action.payload.object;
      state.hostProviders = updateIfExists<AdcmHostProvider>(
        state.hostProviders,
        (hostProvider) =>
          hostProvider.id === hostProviderId && hostProvider.concerns.every((concern) => concern.id !== newConcern.id),
        (hostProvider) => ({
          concerns: [...hostProvider.concerns, newConcern],
        }),
      );
    });
    builder.addCase(wsActions.delete_hostprovider_concern, (state, action) => {
      const { id, changes } = action.payload.object;
      state.hostProviders = updateIfExists<AdcmHostProvider>(
        state.hostProviders,
        (hostProvider) => hostProvider.id === id,
        (hostProvider) => ({
          concerns: hostProvider.concerns.filter((concern) => concern.id !== changes.id),
        }),
      );
    });
  },
});

const { setIsLoading, cleanupHostProviders } = hostProvidersSlice.actions;
export { getHostProviders, cleanupHostProviders, refreshHostProviders, setIsLoading };

export default hostProvidersSlice.reducer;
