import { createSlice } from '@reduxjs/toolkit';
import { AdcmUsersApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { arePromisesResolved } from '@utils/promiseUtils';
import { getUsers, refreshUsers } from './usersSlice';

interface AdcmUsersActionState {
  deleteDialog: {
    id: number | null;
  };
  selectedItemsIds: number[];
}

const blockUsers = createAsyncThunk('adcm/usersActions/blockUsers', async (ids: number[], thunkAPI) => {
  try {
    if (arePromisesResolved(await Promise.allSettled(ids.map((id) => AdcmUsersApi.blockUser(id))))) {
      thunkAPI.dispatch(showInfo({ message: ids.length === 1 ? 'User has been blocked' : 'Users have been blocked' }));
    }
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  } finally {
    thunkAPI.dispatch(refreshUsers());
  }
});

const unblockUsers = createAsyncThunk('adcm/usersActions/unblockUsers', async (ids: number[], thunkAPI) => {
  try {
    if (arePromisesResolved(await Promise.allSettled(ids.map((id) => AdcmUsersApi.unblockUser(id))))) {
      thunkAPI.dispatch(
        showInfo({ message: ids.length === 1 ? 'User has been unblocked' : 'Users have been unblocked' }),
      );
    }
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  } finally {
    thunkAPI.dispatch(refreshUsers());
  }
});

const deleteUsersWithUpdate = createAsyncThunk('adcm/users/deleteUsers', async (ids: number[], thunkAPI) => {
  try {
    if (arePromisesResolved(await Promise.allSettled(ids.map((id) => AdcmUsersApi.deleteUser(id))))) {
      thunkAPI.dispatch(showInfo({ message: ids.length === 1 ? 'User has been deleted' : 'Users have been deleted' }));
      await thunkAPI.dispatch(getUsers());
    }
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const createInitialState = (): AdcmUsersActionState => ({
  deleteDialog: {
    id: null,
  },
  selectedItemsIds: [],
});

const usersActionsSlice = createSlice({
  name: 'adcm/usersActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
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
    builder
      .addCase(deleteUsersWithUpdate.pending, (state) => {
        usersActionsSlice.caseReducers.closeDeleteDialog(state);
      })
      .addCase(blockUsers.fulfilled, (state) => {
        state.selectedItemsIds = [];
      })
      .addCase(unblockUsers.fulfilled, (state) => {
        state.selectedItemsIds = [];
      });
  },
});

const { setSelectedItemsIds, openDeleteDialog, closeDeleteDialog } = usersActionsSlice.actions;
export { deleteUsersWithUpdate, setSelectedItemsIds, openDeleteDialog, closeDeleteDialog, blockUsers, unblockUsers };
export default usersActionsSlice.reducer;
