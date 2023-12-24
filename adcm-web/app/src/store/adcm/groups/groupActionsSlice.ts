import { AdcmGroupsApi, AdcmUsersApi, RequestError } from '@api';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getGroups } from './groupsSlice';
import { AdcmGroup, AdcmUpdateGroupPayload, AdcmCreateGroupPayload, AdcmUser } from '@models/adcm';
import { PaginationParams, SortParams } from '@models/table';

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

interface AdcmGroupsActionsState {
  createDialog: {
    isOpen: boolean;
  };
  updateDialog: {
    group: AdcmGroup | null;
    isUpdating: boolean;
  };
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
      });
  },
});

export const { openCreateDialog, closeCreateDialog, openUpdateDialog, closeUpdateDialog } = groupsActionsSlice.actions;
export { createGroup, updateGroup, loadUsers };

export default groupsActionsSlice.reducer;
