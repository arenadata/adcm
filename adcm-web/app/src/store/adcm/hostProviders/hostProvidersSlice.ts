import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostProvider } from '@models/adcm/hostProvider';
import { createAsyncThunk } from '@store/redux';
import { AdcmHostProvidersApi, RequestError } from '@api';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

type AdcmHostProviderState = {
  hostProviders: AdcmHostProvider[];
  totalCount: number;
  isLoading: boolean;
  itemsForActions: {
    deletableId: number | null;
  };
};

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

const deleteHostProvider = createAsyncThunk(
  'adcm/hostProviders/deleteHostProvider',
  async (deletableId: number, thunkAPI) => {
    try {
      await AdcmHostProvidersApi.deleteHostProvider(deletableId);
      thunkAPI.dispatch(showInfo({ message: 'Hostprovider was deleted' }));
      return [];
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

const deleteWithUpdateHostProviders = createAsyncThunk(
  'adcm/hostProviders/deleteWithUpdateHostProviders',
  async (deletableId: number, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    await thunkAPI.dispatch(deleteHostProvider(deletableId));
    await thunkAPI.dispatch(getHostProviders());
  },
);

const createInitialState = (): AdcmHostProviderState => ({
  hostProviders: [],
  totalCount: 0,
  isLoading: false,
  itemsForActions: {
    deletableId: null,
  },
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
    setDeletableId(state, action) {
      state.itemsForActions.deletableId = action.payload;
    },
    cleanupItemsForActions(state) {
      state.itemsForActions = createInitialState().itemsForActions;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getHostProviders.pending, (state) => {
      hostProvidersSlice.caseReducers.cleanupItemsForActions(state);
    });
    builder.addCase(loadHostProviders.fulfilled, (state, action) => {
      state.hostProviders = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadHostProviders.rejected, (state) => {
      state.hostProviders = [];
    });
    builder.addCase(deleteHostProvider.pending, (state) => {
      state.itemsForActions.deletableId = null;
    });
  },
});

const { setIsLoading, cleanupHostProviders, setDeletableId } = hostProvidersSlice.actions;
export { getHostProviders, cleanupHostProviders, refreshHostProviders, setDeletableId, deleteWithUpdateHostProviders };

export default hostProvidersSlice.reducer;
