import { createSlice } from '@reduxjs/toolkit';
import type { AdcmHostProvider } from '@models/adcm/hostProvider';
import { createAsyncThunk } from '@store/redux';
import { AdcmHostProvidersApi } from '@api';
import { executeWithMinDelay } from '@utils/requestUtils';
import { updateIfExists } from '@utils/objectUtils';
import { defaultSpinnerDelay } from '@constants';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';
import { LoadState } from '@models/loadState';

interface AdcmHostProvidersState {
  hostProviders: AdcmHostProvider[];
  totalCount: number;
  loadState: LoadState;
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
  thunkAPI.dispatch(setLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadHostProviders());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLoadState(LoadState.Loaded));
    },
  });
});

const refreshHostProviders = createAsyncThunk('adcm/hostProviders/refreshHostProviders', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadHostProviders());
});

const createInitialState = (): AdcmHostProvidersState => ({
  hostProviders: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
});

const hostProvidersSlice = createSlice({
  name: 'adcm/hostProviders',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
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
    builder.addCase(wsActions.update_hostprovider, (state, action) => {
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

const { setLoadState, cleanupHostProviders } = hostProvidersSlice.actions;
export { getHostProviders, cleanupHostProviders, refreshHostProviders, setLoadState };

export default hostProvidersSlice.reducer;
