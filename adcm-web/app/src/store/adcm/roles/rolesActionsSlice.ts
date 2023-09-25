import { createSlice } from '@reduxjs/toolkit';
import { RequestError, AdcmRolesApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getRoles } from './rolesSlice';
import { AdcmCreateRolePayload, AdcmRole, AdcmRoleType } from '@models/adcm';

interface AdcmRolesActionState {
  deleteDialog: {
    id: number | null;
  };
  isCreateDialogOpened: boolean;
  relatedData: {
    categories: string[];
    isLoaded: boolean;
    allRoles: AdcmRole[];
  };
}

const createInitialState = (): AdcmRolesActionState => ({
  deleteDialog: {
    id: null,
  },
  isCreateDialogOpened: false,
  relatedData: {
    categories: [],
    isLoaded: false,
    allRoles: [],
  },
});

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

const createRole = createAsyncThunk(
  'adcm/role/createRoleDialog/createRole',
  async (arg: AdcmCreateRolePayload, thunkAPI) => {
    try {
      await AdcmRolesApi.createRole(arg);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getRoles());
    }
  },
);

const loadAllRoles = createAsyncThunk('adcm/role/createRoleDialog/loadAllRoles', async (arg, thunkAPI) => {
  try {
    return await AdcmRolesApi.getRoles({
      type: AdcmRoleType.Business,
    });
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/role/createRoleDialog/loadRelatedData', async (arg, thunkAPI) => {
  await thunkAPI.dispatch(loadAllRoles());
});

const openCreateDialog = createAsyncThunk('adcm/role/createRoleDialog/open', async (arg, thunkAPI) => {
  try {
    thunkAPI.dispatch(loadRelatedData());
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
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
    closeCreateDialog() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(deleteRoleWithUpdate.pending, (state) => {
      rolesActionsSlice.caseReducers.closeDeleteDialog(state);
    });
    builder.addCase(openCreateDialog.fulfilled, (state) => {
      state.isCreateDialogOpened = true;
    });
    builder.addCase(loadRelatedData.fulfilled, (state) => {
      state.relatedData.isLoaded = true;
    });
    builder.addCase(loadAllRoles.fulfilled, (state, action) => {
      state.relatedData.allRoles = action.payload.results;
    });
    builder.addCase(createRole.fulfilled, () => {
      return createInitialState();
    });
  },
});

const { openDeleteDialog, closeDeleteDialog, closeCreateDialog } = rolesActionsSlice.actions;
export { deleteRoleWithUpdate, openDeleteDialog, closeDeleteDialog, openCreateDialog, closeCreateDialog, createRole };
export default rolesActionsSlice.reducer;
