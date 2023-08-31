import { createSlice } from '@reduxjs/toolkit';
import { RequestError, AdcmRolesApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getRoles } from './rolesSlice';

interface AdcmRolesActionState {
  deleteDialog: {
    id: number | null;
  };
}

const deleteRoleWithUpdate = createAsyncThunk('adcm/rolesActions/deleteRoles', async (id: number, thunkAPI) => {
  try {
    await AdcmRolesApi.deleteRole(id);
    thunkAPI.dispatch(showInfo({ message: 'Role has been deleted' }));
    await thunkAPI.dispatch(getRoles());
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const createInitialState = (): AdcmRolesActionState => ({
  deleteDialog: {
    id: null,
  },
});

const rolesActionsSlice = createSlice({
  name: 'adcm/rolesActions',
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
  },
  extraReducers: (builder) => {
    builder.addCase(deleteRoleWithUpdate.pending, (state) => {
      rolesActionsSlice.caseReducers.closeDeleteDialog(state);
    });
  },
});

const { openDeleteDialog, closeDeleteDialog } = rolesActionsSlice.actions;
export { deleteRoleWithUpdate, openDeleteDialog, closeDeleteDialog };
export default rolesActionsSlice.reducer;
