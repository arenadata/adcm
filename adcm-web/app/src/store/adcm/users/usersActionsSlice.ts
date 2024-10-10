import { AdcmGroupsApi, AdcmUsersApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { arePromisesResolved } from '@utils/promiseUtils';
import { getUsers, refreshUsers } from './usersSlice';
import type { AdcmCreateUserPayload, AdcmGroup, AdcmUser, UpdateAdcmUserPayload } from '@models/adcm';
import type { PaginationParams, SortParams } from '@models/table';
import type { ModalState } from '@models/modal';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';

interface AdcmUsersActionState extends ModalState<AdcmUser, 'user'> {
  updateDialog: {
    user: AdcmUser | null;
  };
  deleteDialog: {
    user: AdcmUser | null;
  };
  unblockDialog: {
    user: AdcmUser | null;
  };
  blockDialog: {
    user: AdcmUser | null;
  };
  relatedData: {
    groups: AdcmGroup[];
  };
  selectedUsersIds: number[];
}

const blockUsers = createAsyncThunk('adcm/usersActions/blockUsers', async (ids: number[], thunkAPI) => {
  try {
    if (arePromisesResolved(await Promise.allSettled(ids.map((id) => AdcmUsersApi.blockUser(id))))) {
      thunkAPI.dispatch(
        showSuccess({
          message: ids.length === 1 ? 'User was blocked successfully' : 'Users were blocked successfully',
        }),
      );
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
        showSuccess({
          message: ids.length === 1 ? 'User was unblocked successfully' : 'Users were unblocked successfully',
        }),
      );
    }
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  } finally {
    thunkAPI.dispatch(refreshUsers());
  }
});

const deleteUsersWithUpdate = createAsyncThunk('adcm/usersActions/deleteUsers', async (users: number[], thunkAPI) => {
  try {
    if (arePromisesResolved(await Promise.allSettled(users.map((id) => AdcmUsersApi.deleteUser(id))))) {
      thunkAPI.dispatch(
        showSuccess({ message: users.length === 1 ? 'User has been deleted' : 'Users have been deleted' }),
      );
    }
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  } finally {
    thunkAPI.dispatch(refreshUsers());
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
  async (_user: AdcmUser, thunkAPI) => {
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
    thunkAPI.dispatch(refreshUsers());
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
  try {
    const sortParams: SortParams = {
      sortBy: '',
      sortDirection: 'asc',
    };
    const paginationParams: PaginationParams = {
      pageNumber: 0,
      perPage: 1,
    };
    const batch = await AdcmGroupsApi.getGroups({}, sortParams, paginationParams);
    sortParams.sortBy = 'displayName';
    paginationParams.perPage = batch.count;
    return await AdcmGroupsApi.getGroups({}, sortParams, paginationParams);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): AdcmUsersActionState => ({
  createDialog: {
    isOpen: false,
  },
  deleteDialog: {
    user: null,
  },
  updateDialog: {
    user: null,
  },
  unblockDialog: {
    user: null,
  },
  blockDialog: {
    user: null,
  },
  relatedData: {
    groups: [],
  },
  selectedUsersIds: [],
});

const usersActionsSlice = createCrudSlice({
  name: 'adcm/usersActions',
  entityName: 'user',
  createInitialState,
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    setSelectedUsersIds(state, action) {
      state.selectedUsersIds = action.payload;
    },
    openUnblockDialog(state, action) {
      state.unblockDialog.user = action.payload;
    },
    closeUnblockDialog(state) {
      state.unblockDialog.user = null;
    },
    openBlockDialog(state, action) {
      state.blockDialog.user = action.payload;
    },
    closeBlockDialog(state) {
      state.blockDialog.user = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(deleteUsersWithUpdate.pending, (state) => {
        state.selectedUsersIds = [];
        usersActionsSlice.caseReducers.closeDeleteDialog(state);
      })
      .addCase(blockUsers.fulfilled, (state) => {
        state.selectedUsersIds = [];
        usersActionsSlice.caseReducers.closeBlockDialog(state);
      })
      .addCase(blockUsers.rejected, (state) => {
        usersActionsSlice.caseReducers.closeBlockDialog(state);
      })
      .addCase(unblockUsers.fulfilled, (state) => {
        state.selectedUsersIds = [];
        usersActionsSlice.caseReducers.closeUnblockDialog(state);
      })
      .addCase(unblockUsers.rejected, (state) => {
        usersActionsSlice.caseReducers.closeUnblockDialog(state);
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
      .addCase(loadGroups.rejected, (state) => {
        state.relatedData.groups = [];
      })
      .addCase(createUser.pending, (state) => {
        state.isActionInProgress = true;
      })
      .addCase(createUser.fulfilled, (state) => {
        usersActionsSlice.caseReducers.closeCreateDialog(state);
      })
      .addCase(createUser.rejected, (state) => {
        state.isActionInProgress = false;
      })
      .addCase(updateUser.pending, (state) => {
        state.isActionInProgress = true;
      })
      .addCase(updateUser.fulfilled, (state) => {
        usersActionsSlice.caseReducers.closeUpdateDialog(state);
      })
      .addCase(updateUser.rejected, (state) => {
        state.isActionInProgress = false;
      });
  },
});

export const {
  setSelectedUsersIds,
  openDeleteDialog,
  closeDeleteDialog,
  closeUpdateDialog: closeUserUpdateDialog,
  closeCreateDialog: closeUserCreateDialog,
  openUnblockDialog,
  closeUnblockDialog,
  openBlockDialog,
  closeBlockDialog,
} = usersActionsSlice.actions;

export {
  deleteUsersWithUpdate,
  blockUsers,
  unblockUsers,
  createUser,
  updateUser,
  openUserCreateDialog,
  openUserUpdateDialog,
};
export default usersActionsSlice.reducer;
