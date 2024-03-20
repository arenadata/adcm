import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { getBundles, refreshBundles, setLoadState } from './bundlesSlice';
import { AdcmBundlesApi, RequestError } from '@api';
import { LoadState } from '@models/loadState';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { rejectedFilter } from '@utils/promiseUtils';
import { loadRelatedData } from './bundlesTableSlice';

interface AdcmBundlesActionsState {
  isUploading: boolean;
  deleteDialog: {
    id: number | null;
  };
  selectedItemsIds: number[];
}

const deleteBundles = createAsyncThunk(
  'adcm/bundlesActions/deleteBundles',
  async (selectedBundlesIds: number[], thunkAPI) => {
    try {
      const deletePromises = await Promise.allSettled(selectedBundlesIds.map((id) => AdcmBundlesApi.deleteBundle(id)));
      const responsesList = rejectedFilter(deletePromises);

      if (responsesList.length > 0) {
        throw responsesList[0];
      }
      const message =
        selectedBundlesIds.length > 1 ? 'All selected bundles have been deleted' : 'The bundle has been deleted';
      thunkAPI.dispatch(showSuccess({ message }));
      return [];
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

/**
 * Deleted some bundles
 * And update bundles list
 */
const deleteWithUpdateBundles = createAsyncThunk(
  'adcm/bundlesActions/deleteWithUpdateBundles',
  async (selectedBundlesIds: number[], thunkAPI) => {
    thunkAPI.dispatch(setLoadState(LoadState.Loading));
    await thunkAPI.dispatch(deleteBundles(selectedBundlesIds));
    await thunkAPI.dispatch(getBundles());
    await thunkAPI.dispatch(loadRelatedData());
    thunkAPI.dispatch(setLoadState(LoadState.Loaded));
  },
);

const uploadBundles = createAsyncThunk('adcm/bundlesActions/uploadBundles', async (files: File[], thunkAPI) => {
  thunkAPI.dispatch(setIsUploading(true));
  const uploadPromises = await Promise.allSettled(
    files.map(async (file) => {
      try {
        const res = await AdcmBundlesApi.uploadBundle(file);
        thunkAPI.dispatch(showSuccess({ message: `Bundle "${file.name}" was upload success` }));
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
  'adcm/bundlesActions/uploadWithUpdateBundles',
  async (files: File[], thunkAPI) => {
    await thunkAPI.dispatch(uploadBundles(files));
    await thunkAPI.dispatch(getBundles());
    await thunkAPI.dispatch(loadRelatedData());
  },
);

const createInitialState = (): AdcmBundlesActionsState => ({
  isUploading: false,
  deleteDialog: {
    id: null,
  },
  selectedItemsIds: [],
});

const bundlesActionsSlice = createSlice({
  name: 'adcm/bundlesActions',
  initialState: createInitialState(),
  reducers: {
    setIsUploading(state, action) {
      state.isUploading = action.payload;
    },
    openDeleteDialog(state, action) {
      state.deleteDialog.id = action.payload;
    },
    closeDeleteDialog(state) {
      state.deleteDialog.id = null;
    },
    setSelectedItemsIds(state, action) {
      state.selectedItemsIds = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(deleteBundles.pending, (state) => {
      // hide dialog, when
      state.deleteDialog.id = null;
    });
    builder.addCase(getBundles.pending, (state) => {
      // hide dialogs, when load new bundles list (not silent refresh)
      bundlesActionsSlice.caseReducers.closeDeleteDialog(state);
    });
    // brake selected rows after full update
    builder.addCase(getBundles.fulfilled, (state) => {
      state.selectedItemsIds = [];
    });
  },
});

export const { setIsUploading, openDeleteDialog, closeDeleteDialog, setSelectedItemsIds } = bundlesActionsSlice.actions;
export { getBundles, refreshBundles, deleteBundles, deleteWithUpdateBundles, uploadWithUpdateBundles };

export default bundlesActionsSlice.reducer;
