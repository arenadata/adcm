import { AdcmGroupsApi, RequestError } from '@api';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getGroups } from './groupsSlice';
import { AdcmGroup, AdcmUpdateGroupPayload, AdcmCreateGroupPayload } from '@models/adcm';

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

interface AdcmGroupsActionsState {
  createDialog: {
    isOpen: boolean;
  };
  updateDialog: {
    group: AdcmGroup | null;
    isUpdating: boolean;
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
        state.updateDialog.isUpdating = false;
        groupsActionsSlice.caseReducers.closeUpdateDialog(state);
      });
  },
});

export const { openCreateDialog, closeCreateDialog, openUpdateDialog, closeUpdateDialog } = groupsActionsSlice.actions;
export { createGroup, updateGroup };

export default groupsActionsSlice.reducer;
