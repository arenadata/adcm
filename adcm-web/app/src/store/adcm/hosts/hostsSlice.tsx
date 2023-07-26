import { AdcmHost } from '@models/adcm/host';
import { createAsyncThunk } from '@store/redux';
import { AdcmHostsApi } from '@api/adcm/hosts';
import { defaultSpinnerDelay } from '@constants';
import { executeWithMinDelay } from '@utils/requestUtils';
import { rejectedFilter } from '@utils/promiseUtils';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { RequestError } from '@api';
import { createSlice } from '@reduxjs/toolkit';

type AdcmHostsState = {
  hosts: AdcmHost[];
  totalCount: number;
  isLoading: boolean;
  isUploading: boolean;
  itemsForActions: {
    deletableId: number | null;
  };
};

type DeleteHostsArg = {
  ids: number[];
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

const deleteHosts = createAsyncThunk('adcm/hosts/deleteHosts', async ({ ids }: DeleteHostsArg, thunkAPI) => {
  try {
    const deletePromises = await Promise.allSettled(ids.map((id) => AdcmHostsApi.deleteHost(id)));
    const responsesList = rejectedFilter(deletePromises);

    if (responsesList.length > 0) {
      throw responsesList[0];
    }
    thunkAPI.dispatch(showInfo({ message: 'All selected hosts were deleted' }));
    return [];
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue([]);
  }
});

/**
 * Deleted some bundles
 * And update bundles list
 */
const deleteWithUpdateHosts = createAsyncThunk(
  'adcm/bundles/deleteWithUpdateBundles',
  async (selectedHostsIds: number[], thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    await thunkAPI.dispatch(deleteHosts({ ids: selectedHostsIds }));
    await thunkAPI.dispatch(getHosts());
    thunkAPI.dispatch(setIsLoading(false));
  },
);

const createInitialState = (): AdcmHostsState => ({
  hosts: [],
  totalCount: 0,
  isLoading: false,
  isUploading: false,
  itemsForActions: {
    deletableId: null,
  },
});

const hostsSlice = createSlice({
  name: 'adcm/hosts',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    setIsUploading(state, action) {
      state.isUploading = action.payload;
    },
    cleanupHosts() {
      return createInitialState();
    },
    cleanupItemsForActions(state) {
      state.itemsForActions = createInitialState().itemsForActions;
    },
    setDeletableId(state, action) {
      state.itemsForActions.deletableId = action.payload;
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

    builder.addCase(deleteHosts.pending, (state) => {
      // hide dialog, when
      state.itemsForActions.deletableId = null;
    });
    builder.addCase(getHosts.pending, (state) => {
      // hide dialogs, when load new bundles list (not silent refresh)
      hostsSlice.caseReducers.cleanupItemsForActions(state);
    });
  },
});

export const { setIsLoading, cleanupHosts, setIsUploading, setDeletableId, cleanupItemsForActions } =
  hostsSlice.actions;
export { getHosts, refreshHosts, deleteHosts, deleteWithUpdateHosts };

export default hostsSlice.reducer;
