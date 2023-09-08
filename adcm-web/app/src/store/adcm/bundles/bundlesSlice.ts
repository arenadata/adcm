import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmBundle } from '@models/adcm/bundle';
import { AdcmBundlesApi, RequestError } from '@api';
import { rejectedFilter } from '@utils/promiseUtils';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

type AdcmBundlesState = {
  bundles: AdcmBundle[];
  totalCount: number;
  isLoading: boolean;
  isUploading: boolean;
  itemsForActions: {
    deletableId: number | null;
  };
  selectedItemsIds: number[];
};

const loadBundles = createAsyncThunk('adcm/bundles/loadBundles', async (arg, thunkAPI) => {
  const {
    adcm: {
      bundlesTable: { filter, sortParams, paginationParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmBundlesApi.getBundles(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getBundles = createAsyncThunk('adcm/bundles/getBundles', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadBundles());
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshBundles = createAsyncThunk('adcm/bundles/refreshBundles', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadBundles());
});

const deleteBundles = createAsyncThunk('adcm/bundles/deleteBundles', async (selectedBundlesIds: number[], thunkAPI) => {
  try {
    const deletePromises = await Promise.allSettled(selectedBundlesIds.map((id) => AdcmBundlesApi.deleteBundle(id)));
    const responsesList = rejectedFilter(deletePromises);

    if (responsesList.length > 0) {
      throw responsesList[0];
    }
    const message =
      selectedBundlesIds.length > 1 ? 'All selected bundles have been deleted' : 'The bundle has been deleted';
    thunkAPI.dispatch(showInfo({ message }));
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
const deleteWithUpdateBundles = createAsyncThunk(
  'adcm/bundles/deleteWithUpdateBundles',
  async (selectedBundlesIds: number[], thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    await thunkAPI.dispatch(deleteBundles(selectedBundlesIds));
    await thunkAPI.dispatch(getBundles());
    thunkAPI.dispatch(setIsLoading(false));
  },
);

const uploadBundles = createAsyncThunk('adcm/bundles/uploadBundles', async (files: File[], thunkAPI) => {
  thunkAPI.dispatch(setIsUploading(true));
  const uploadPromises = await Promise.allSettled(
    files.map(async (file) => {
      try {
        const res = await AdcmBundlesApi.uploadBundle(file);
        thunkAPI.dispatch(showInfo({ message: `Bundle "${file.name}" was upload success` }));
        return res;
      } catch (error) {
        thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
        return error;
      }
    }),
  );
  const rejectedResponsesList = rejectedFilter(uploadPromises);

  thunkAPI.dispatch(setIsUploading(false));

  if (rejectedResponsesList.length > 0) {
    return thunkAPI.rejectWithValue([]);
  } else {
    return thunkAPI.fulfillWithValue([]);
  }
});

const uploadWithUpdateBundles = createAsyncThunk(
  'adcm/bundles/uploadWithUpdateBundles',
  async (files: File[], thunkAPI) => {
    await thunkAPI.dispatch(uploadBundles(files));
    await thunkAPI.dispatch(getBundles());
  },
);

const createInitialState = (): AdcmBundlesState => ({
  bundles: [],
  totalCount: 0,
  isLoading: false,
  isUploading: false,
  itemsForActions: {
    deletableId: null,
  },
  selectedItemsIds: [],
});

const bundlesSlice = createSlice({
  name: 'adcm/bundles',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    setIsUploading(state, action) {
      state.isUploading = action.payload;
    },
    cleanupBundles() {
      return createInitialState();
    },
    cleanupItemsForActions(state) {
      state.itemsForActions = createInitialState().itemsForActions;
    },
    setSelectedItemsIds(state, action) {
      state.selectedItemsIds = action.payload;
    },
    setDeletableId(state, action) {
      state.itemsForActions.deletableId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadBundles.fulfilled, (state, action) => {
      state.bundles = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadBundles.rejected, (state) => {
      state.bundles = [];
    });

    builder.addCase(deleteBundles.pending, (state) => {
      // hide dialog, when
      state.itemsForActions.deletableId = null;
    });
    builder.addCase(getBundles.pending, (state) => {
      // hide dialogs, when load new bundles list (not silent refresh)
      bundlesSlice.caseReducers.cleanupItemsForActions(state);
    });
    // brake selected rows after full update
    builder.addCase(getBundles.fulfilled, (state) => {
      state.selectedItemsIds = [];
    });
  },
});

export const {
  setIsLoading,
  cleanupBundles,
  setIsUploading,
  setDeletableId,
  cleanupItemsForActions,
  setSelectedItemsIds,
} = bundlesSlice.actions;
export { getBundles, refreshBundles, deleteBundles, deleteWithUpdateBundles, uploadWithUpdateBundles };

export default bundlesSlice.reducer;
