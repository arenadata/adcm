import { AdcmGroupsApi, AdcmUsersApi, RequestError } from '@api';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getGroups } from './groupsSlice';
import { AdcmGroup, AdcmUpdateGroupPayload, AdcmCreateGroupPayload, AdcmUser } from '@models/adcm';
import { PaginationParams, SortParams } from '@models/table';
import { rejectedFilter } from '@utils/promiseUtils';

const createGroup = createAsyncThunk(
  'adcm/groupActions/createGroup',
  async (payload: AdcmCreateGroupPayload, thunkAPI) => {
    try {
      const group = await AdcmGroupsApi.createGroup(payload);
      return group;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getGroups());
    }
  },
);

interface UpdateGroupPayload {
  id: number;
  data: AdcmUpdateGroupPayload;
}

const updateGroup = createAsyncThunk(
  'adcm/groupActions/updateGroup',
  async ({ id, data }: UpdateGroupPayload, thunkAPI) => {
    try {
      const group = await AdcmGroupsApi.updateGroup(id, data);
      return group;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getGroups());
    }
  },
);

const loadUsers = createAsyncThunk('adcm/groupActions/loadUsers', async (arg, thunkAPI) => {
  try {
    const sortParams: SortParams = {
      sortBy: '',
      sortDirection: 'asc',
    };
    const paginationParams: PaginationParams = {
      pageNumber: 0,
      perPage: 1,
    };
    const batch = await AdcmUsersApi.getUsers({}, sortParams, paginationParams);
    sortParams.sortBy = 'username';
    paginationParams.perPage = batch.count;
    return await AdcmUsersApi.getUsers({}, sortParams, paginationParams);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const deleteGroupsWithUpdate = createAsyncThunk('adcm/groupActions/deleteGroups', async (ids: number[], thunkAPI) => {
  try {
    const deletePromises = await Promise.allSettled(ids.map((id) => AdcmGroupsApi.deleteGroup(id)));
    const responsesList = rejectedFilter(deletePromises);

    if (responsesList.length > 0) {
      throw responsesList[0];
    }

    await thunkAPI.dispatch(getGroups());
    thunkAPI.dispatch(showInfo({ message: 'Groups have been deleted' }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

interface AdcmGroupsActionsState {
  createDialog: {
    isOpen: boolean;
  };
  updateDialog: {
    group: AdcmGroup | null;
    isUpdating: boolean;
  };
  deleteDialog: {
    id: number | null;
  };
  selectedItemsIds: number[];
  relatedData: {
    users: AdcmUser[];
  };
}

const createInitialState = (): AdcmGroupsActionsState => ({
  createDialog: {
    isOpen: false,
  },
  updateDialog: {
    group: null,
    isUpdating: false,
  },
  deleteDialog: {
    id: null,
  },
  selectedItemsIds: [],
  relatedData: {
    users: [],
  },
});

const groupsActionsSlice = createSlice({
  name: 'adcm/groupsActions',
  initialState: createInitialState(),
  reducers: {
    cleanupGroups() {
      return createInitialState();
    },
    openCreateDialog(state) {
      state.createDialog.isOpen = true;
    },
    closeCreateDialog(state) {
      state.createDialog.isOpen = false;
    },
    openUpdateDialog(state, action) {
      state.updateDialog.group = action.payload;
    },
    closeUpdateDialog(state) {
      state.updateDialog.group = null;
      state.updateDialog.isUpdating = false;
    },
    cleanupItemsForActions(state) {
      state.selectedItemsIds = createInitialState().selectedItemsIds;
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
      .addCase(createGroup.fulfilled, (state) => {
        groupsActionsSlice.caseReducers.closeCreateDialog(state);
      })
      .addCase(updateGroup.pending, (state) => {
        state.updateDialog.isUpdating = true;
      })
      .addCase(updateGroup.fulfilled, (state) => {
        groupsActionsSlice.caseReducers.closeUpdateDialog(state);
      })
      .addCase(updateGroup.rejected, (state) => {
        state.updateDialog.isUpdating = false;
      })
      .addCase(loadUsers.fulfilled, (state, action) => {
        state.relatedData.users = action.payload.results;
      })
      .addCase(loadUsers.rejected, (state) => {
        state.relatedData.users = [];
      })
      .addCase(deleteGroupsWithUpdate.pending, (state) => {
        state.deleteDialog.id = null;
      })
      .addCase(getGroups.pending, (state) => {
        state.selectedItemsIds = [];
      });
  },
});

export const {
  openCreateDialog,
  closeCreateDialog,
  openUpdateDialog,
  cleanupItemsForActions,
  closeUpdateDialog,
  openDeleteDialog,
  closeDeleteDialog,
  setSelectedItemsIds,
} = groupsActionsSlice.actions;
export { createGroup, updateGroup, loadUsers, deleteGroupsWithUpdate };

export default groupsActionsSlice.reducer;
