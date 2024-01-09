import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmHostProvidersApi, RequestError } from '@api';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getHostProviders, setLoadState } from './hostProvidersSlice';
import { LoadState } from '@models/loadState';

interface AdcmHostProvidersActionsState {
  deleteDialog: {
    id: number | null;
  };
}

const deleteHostProvider = createAsyncThunk(
  'adcm/hostProvidersActions/deleteHostProvider',
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

const deleteWithUpdateHostProvider = createAsyncThunk(
  'adcm/hostProvidersActions/deleteWithUpdateHostProvider',
  async (deletableId: number, thunkAPI) => {
    thunkAPI.dispatch(setLoadState(LoadState.Loading));
    await thunkAPI.dispatch(deleteHostProvider(deletableId));
    await thunkAPI.dispatch(getHostProviders());
  },
);

const createInitialState = (): AdcmHostProvidersActionsState => ({
  deleteDialog: {
    id: null,
  },
});

const hostProvidersActionsSlice = createSlice({
  name: 'adcm/hostProvidersActions',
  initialState: createInitialState(),
  reducers: {
    cleanupHostProvidersActions() {
      return createInitialState();
    },
    openDeleteDialog(state, action) {
      state.deleteDialog.id = action.payload;
    },
    closeDeleteDialog(state) {
      state.deleteDialog.id = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(deleteWithUpdateHostProvider.pending, (state) => {
      hostProvidersActionsSlice.caseReducers.closeDeleteDialog(state);
    });
  },
});

const { openDeleteDialog, closeDeleteDialog } = hostProvidersActionsSlice.actions;
export { openDeleteDialog, closeDeleteDialog, deleteWithUpdateHostProvider, deleteHostProvider };

export default hostProvidersActionsSlice.reducer;
