import type { RequestError } from '@api';
import { AdcmRolesApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getRoles } from './rolesSlice';
import { type AdcmCreateRolePayload, type AdcmRole, AdcmRoleType, type UpdateRolePayload } from '@models/adcm';
import type { SortParams } from '@models/table';
import type { ModalState } from '@models/modal';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';

interface AdcmRolesActionState extends ModalState<AdcmRole, 'role'> {
  deleteDialog: {
    role: AdcmRole | null;
  };
  updateDialog: {
    role: AdcmRole | null;
  };
  relatedData: {
    categories: string[];
    isLoaded: boolean;
    allRoles: AdcmRole[];
  };
}

const createInitialState = (): AdcmRolesActionState => ({
  createDialog: {
    isOpen: false,
  },
  deleteDialog: {
    role: null,
  },
  updateDialog: {
    role: null,
  },
  relatedData: {
    categories: [],
    isLoaded: false,
    allRoles: [],
  },
});

const deleteRoleWithUpdate = createAsyncThunk('adcm/rolesActions/deleteRoles', async (role: AdcmRole, thunkAPI) => {
  try {
    await AdcmRolesApi.deleteRole(role.id);
    thunkAPI.dispatch(showSuccess({ message: 'Role has been deleted' }));
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

const updateRole = createAsyncThunk(
  'adcm/role/editRoleDialog/updateRole',
  async ({ id, data }: UpdateRolePayload, thunkAPI) => {
    try {
      await AdcmRolesApi.updateRole(id, data);
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
    const sortParams = {
      sortBy: 'displayName',
      sortDirection: 'asc',
    } as SortParams;

    const { count, results } = await AdcmRolesApi.getRoles(
      {
        type: AdcmRoleType.Business,
      },
      sortParams,
    );
    if (count === results.length) {
      return results;
    }

    // count > results.length
    const { results: roles } = await AdcmRolesApi.getRoles(
      {
        type: AdcmRoleType.Business,
      },
      sortParams,
      {
        perPage: count,
        pageNumber: 0,
      },
    );

    return roles;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/role/createRoleDialog/loadRelatedData', async (arg, thunkAPI) => {
  await thunkAPI.dispatch(loadAllRoles());
});

const rolesActionsSlice = createCrudSlice({
  name: 'adcm/rolesActions',
  entityName: 'role',
  createInitialState,
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(deleteRoleWithUpdate.pending, (state) => {
      rolesActionsSlice.caseReducers.closeDeleteDialog(state);
    });
    builder.addCase(loadRelatedData.fulfilled, (state) => {
      state.relatedData.isLoaded = true;
    });
    builder.addCase(loadAllRoles.fulfilled, (state, action) => {
      state.relatedData.allRoles = action.payload;
    });
    builder.addCase(loadAllRoles.rejected, (state) => {
      state.relatedData.allRoles = [];
    });
    builder.addCase(createRole.fulfilled, () => {
      return createInitialState();
    });
    builder.addCase(updateRole.fulfilled, () => {
      return createInitialState();
    });
  },
});

const {
  openDeleteDialog,
  openCreateDialog,
  openUpdateDialog,
  closeUpdateDialog,
  closeDeleteDialog,
  closeCreateDialog,
} = rolesActionsSlice.actions;
export {
  deleteRoleWithUpdate,
  openDeleteDialog,
  closeDeleteDialog,
  openCreateDialog,
  closeCreateDialog,
  createRole,
  openUpdateDialog,
  closeUpdateDialog,
  updateRole,
  loadRelatedData,
};
export default rolesActionsSlice.reducer;
