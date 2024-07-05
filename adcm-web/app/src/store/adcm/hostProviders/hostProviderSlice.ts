import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostProvider } from '@models/adcm/hostProvider';
import { createAsyncThunk } from '@store/redux';
import { AdcmHostProvidersApi, AdcmHostsApi, RequestError } from '@api';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';
import { showError } from '@store/notificationsSlice';
import { RequestState } from '@models/loadState';
import { processErrorResponse } from '@utils/responseUtils';

interface AdcmHostProviderState {
  hostProvider: AdcmHostProvider | null;
  hostsCount: number;
  accessCheckStatus: RequestState;
}

const getHostsCount = createAsyncThunk(
  'adcm/hostProvider/getHostsCount',
  async (hostproviderName: string, thunkAPI) => {
    try {
      const batch = await AdcmHostsApi.getHosts(
        { hostproviderName },
        { sortBy: '', sortDirection: 'asc' },
        { perPage: 1, pageNumber: 1 },
      );
      return batch;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getHostProvider = createAsyncThunk('adcm/hostProvider/getHostProvider', async (id: number, thunkAPI) => {
  try {
    return await AdcmHostProvidersApi.getHostProvider(id);
  } catch (error) {
    thunkAPI.dispatch(showError({ message: 'Hostprovider not found' }));
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): AdcmHostProviderState => ({
  hostProvider: null,
  hostsCount: 0,
  accessCheckStatus: RequestState.NotRequested,
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
      state.accessCheckStatus = RequestState.Completed;
      state.hostProvider = action.payload;
    });
    builder.addCase(getHostProvider.rejected, (state, action) => {
      state.accessCheckStatus = processErrorResponse(action?.payload as RequestError);
      state.hostProvider = null;
    });
    builder.addCase(getHostsCount.fulfilled, (state, action) => {
      state.hostsCount = action.payload.count;
    });
    builder.addCase(wsActions.update_provider, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.hostProvider?.id == id) {
        state.hostProvider = {
          ...state.hostProvider,
          ...changes,
        };
      }
    });
    builder.addCase(wsActions.create_hostprovider_concern, (state, action) => {
      const { id: hostProviderId, changes: newConcern } = action.payload.object;
      if (
        state.hostProvider?.id === hostProviderId &&
        state.hostProvider.concerns.every((concern) => concern.id !== newConcern.id)
      ) {
        state.hostProvider = {
          ...state.hostProvider,
          concerns: [...state.hostProvider.concerns, newConcern],
        };
      }
    });
    builder.addCase(wsActions.delete_hostprovider_concern, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.hostProvider?.id === id) {
        state.hostProvider = {
          ...state.hostProvider,
          concerns: state.hostProvider.concerns.filter((concern) => concern.id !== changes.id),
        };
      }
    });
  },
});

const { cleanupHostProvider } = hostProviderSlice.actions;
export { getHostProvider, getHostsCount, cleanupHostProvider };

export default hostProviderSlice.reducer;
