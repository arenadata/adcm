import { AdcmGroupsApi, AdcmUsersApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getGroups } from './groupsSlice';
import { AdcmGroup, AdcmUpdateGroupPayload, AdcmCreateGroupPayload, AdcmUser } from '@models/adcm';
import { PaginationParams, SortParams } from '@models/table';
import { rejectedFilter } from '@utils/promiseUtils';
import { ModalState } from '@models/modal';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';

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
    const message = ids.length > 1 ? 'Groups have been deleted' : 'Group has been deleted';
    thunkAPI.dispatch(showSuccess({ message }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

interface AdcmGroupsActionsState extends ModalState<AdcmGroup, 'group'> {
  createDialog: {
    isOpen: boolean;
  };
  updateDialog: {
    group: AdcmGroup | null;
  };
  deleteDialog: {
    group: number | null;
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
  },
  deleteDialog: {
    group: null,
  },
  selectedItemsIds: [],
  relatedData: {
    users: [],
  },
});

const groupsActionsSlice = createCrudSlice({
  name: 'adcm/groupsActions',
  entityName: 'group',
  createInitialState,
  reducers: {
    cleanupGroups() {
      return createInitialState();
    },
    cleanupItemsForActions(state) {
      state.selectedItemsIds = createInitialState().selectedItemsIds;
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
        state.isActionInProgress = true;
      })
      .addCase(updateGroup.fulfilled, (state) => {
        groupsActionsSlice.caseReducers.closeUpdateDialog(state);
      })
      .addCase(updateGroup.rejected, (state) => {
        state.isActionInProgress = false;
      })
      .addCase(loadUsers.fulfilled, (state, action) => {
        state.relatedData.users = action.payload.results;
      })
      .addCase(loadUsers.rejected, (state) => {
        state.relatedData.users = [];
      })
      .addCase(deleteGroupsWithUpdate.pending, (state) => {
        state.deleteDialog.group = null;
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
