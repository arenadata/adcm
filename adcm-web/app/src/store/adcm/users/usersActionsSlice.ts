import { createSlice } from '@reduxjs/toolkit';
import { AdcmGroupsApi, AdcmUsersApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { arePromisesResolved } from '@utils/promiseUtils';
import { getUsers, refreshUsers } from './usersSlice';
import { AdcmCreateUserPayload, AdcmGroup, AdcmUser, UpdateAdcmUserPayload } from '@models/adcm';

interface AdcmUsersActionState {
  deleteDialog: {
    id: number | null;
  };
  createDialog: {
    isOpen: boolean;
    isCreating: boolean;
  };
  updateDialog: {
    user: AdcmUser | null;
    isUpdating: boolean;
  };
  relatedData: {
    groups: AdcmGroup[];
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

const deleteUsersWithUpdate = createAsyncThunk('adcm/usersActions/deleteUsers', async (ids: number[], thunkAPI) => {
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

const openUserCreateDialog = createAsyncThunk('adcm/usersActions/openUserCreateDialog', async (arg, thunkAPI) => {
  try {
    thunkAPI.dispatch(loadGroups());
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const openUserUpdateDialog = createAsyncThunk(
  'adcm/usersActions/openUserUpdateDialog',
  async (user: AdcmUser, thunkAPI) => {
    try {
      thunkAPI.dispatch(loadGroups());
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createUser = createAsyncThunk('adcm/usersActions/createUser', async (arg: AdcmCreateUserPayload, thunkAPI) => {
  try {
    await AdcmUsersApi.createUser(arg);
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  } finally {
    thunkAPI.dispatch(getUsers());
  }
});

type UpdateUserPayload = {
  id: number;
  userData: UpdateAdcmUserPayload;
};

const updateUser = createAsyncThunk(
  'adcm/usersActions/updateUser',
  async ({ id, userData }: UpdateUserPayload, thunkAPI) => {
    try {
      await AdcmUsersApi.updateUser(id, userData);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getUsers());
    }
  },
);

const loadGroups = createAsyncThunk('adcm/usersActions/loadGroups', async (arg, thunkAPI) => {
  // TODO: remove comment after backend fix
  // const sortParams = {
  //   sortBy: 'displayName',
  //   sortDirection: 'asc',
  // };

  try {
    const groups = await AdcmGroupsApi.getGroups();
    return groups;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): AdcmUsersActionState => ({
  deleteDialog: {
    id: null,
  },
  createDialog: {
    isOpen: false,
    isCreating: false,
  },
  updateDialog: {
    user: null,
    isUpdating: false,
  },
  relatedData: {
    groups: [],
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
    closeUserCreateDialog(state) {
      state.createDialog = createInitialState().createDialog;
    },
    closeUserUpdateDialog(state) {
      state.updateDialog = createInitialState().updateDialog;
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
      })
      .addCase(openUserCreateDialog.pending, (state) => {
        state.createDialog.isOpen = true;
      })
      .addCase(openUserUpdateDialog.pending, (state, action) => {
        state.updateDialog.user = action.meta.arg;
      })
      .addCase(loadGroups.fulfilled, (state, action) => {
        state.relatedData.groups = action.payload.results;
      })
      .addCase(createUser.pending, (state) => {
        state.createDialog.isCreating = true;
      })
      .addCase(createUser.fulfilled, (state) => {
        usersActionsSlice.caseReducers.closeUserCreateDialog(state);
      })
      .addCase(updateUser.pending, (state) => {
        state.updateDialog.isUpdating = true;
      })
      .addCase(updateUser.fulfilled, (state) => {
        usersActionsSlice.caseReducers.closeUserUpdateDialog(state);
      });
  },
});

const { setSelectedItemsIds, openDeleteDialog, closeDeleteDialog, closeUserCreateDialog, closeUserUpdateDialog } =
  usersActionsSlice.actions;

export {
  deleteUsersWithUpdate,
  setSelectedItemsIds,
  openDeleteDialog,
  closeDeleteDialog,
  blockUsers,
  unblockUsers,
  createUser,
  updateUser,
  openUserCreateDialog,
  closeUserCreateDialog,
  openUserUpdateDialog,
  closeUserUpdateDialog,
};
export default usersActionsSlice.reducer;
