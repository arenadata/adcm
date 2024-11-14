import type { AdcmHost } from '@models/adcm/host';
import { createAsyncThunk } from '@store/redux';
import { defaultSpinnerDelay } from '@constants';
import { executeWithMinDelay } from '@utils/requestUtils';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostsApi } from '@api';
import { updateIfExists } from '@utils/objectUtils';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';
import { LoadState } from '@models/loadState';

type AdcmHostsState = {
  hosts: AdcmHost[];
  totalCount: number;
  loadState: LoadState;
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
  thunkAPI.dispatch(setLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadHosts());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLoadState(LoadState.Loaded));
    },
  });
});

const refreshHosts = createAsyncThunk('adcm/hosts/refreshHosts', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadHosts());
});

const createInitialState = (): AdcmHostsState => ({
  hosts: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
});

const hostsSlice = createSlice({
  name: 'adcm/hosts',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
    cleanupHosts() {
      return createInitialState();
    },
    setHostMaintenanceMode(state, action) {
      const changedHost = state.hosts.find(({ id }) => id === action.payload.hostId);
      if (changedHost) {
        changedHost.maintenanceMode = action.payload.maintenanceMode;
      }
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
    builder.addCase(wsActions.update_host, (state, action) => {
      const { id, changes } = action.payload.object;
      state.hosts = updateIfExists<AdcmHost>(
        state.hosts,
        (host) => host.id === id,
        () => changes,
      );
    });
    builder.addCase(wsActions.create_host_concern, (state, action) => {
      const { id: hostId, changes: newConcern } = action.payload.object;
      state.hosts = updateIfExists<AdcmHost>(
        state.hosts,
        (host) => host.id === hostId && host.concerns.every((concern) => concern.id !== newConcern.id),
        (host) => ({
          concerns: [...host.concerns, newConcern],
        }),
      );
    });
    builder.addCase(wsActions.delete_host_concern, (state, action) => {
      const { id, changes } = action.payload.object;
      state.hosts = updateIfExists<AdcmHost>(
        state.hosts,
        (host) => host.id === id,
        (host) => ({
          concerns: host.concerns.filter((concern) => concern.id !== changes.id),
        }),
      );
    });
  },
});

export const { setLoadState, cleanupHosts, setHostMaintenanceMode } = hostsSlice.actions;
export { getHosts, refreshHosts };

export default hostsSlice.reducer;
