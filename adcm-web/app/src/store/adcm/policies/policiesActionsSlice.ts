import { AdcmGroupsApi, AdcmPoliciesApi, AdcmRolesApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { getPolicies } from './policiesSlice';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import {
  AdcmGroup,
  AdcmPolicy,
  AdcmPolicyPayload,
  AdcmPolicyUpdatePayload,
  AdcmRole,
  AdcmRoleType,
} from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';
import { PaginationParams, SortParams } from '@models/table';

interface AdcmPoliciesActionState {
  isAddPolicyDialogOpen: boolean;
  isCreating: boolean;
  deleteDialog: {
    id: number | null;
  };
  editDialog: {
    policy: AdcmPolicy | null;
    roleId: number | null;
  };
  relatedData: {
    roles: AdcmRole[];
    groups: AdcmGroup[];
  };
}

const openPoliciesAddDialog = createAsyncThunk('adcm/policiesActions/openPoliciesAddDialog', async (arg, thunkAPI) => {
  try {
    await Promise.all([thunkAPI.dispatch(loadRoles()), thunkAPI.dispatch(loadGroups())]);
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const openPoliciesEditDialog = createAsyncThunk(
  'adcm/policiesActions/openPoliciesEditDialog',
  async (policy: AdcmPolicy, thunkAPI) => {
    thunkAPI.dispatch(setEditMode(policy));
    try {
      thunkAPI.dispatch(openPoliciesAddDialog());
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createPolicy = createAsyncThunk('adcm/policiesActions/createPolicy', async (arg: AdcmPolicyPayload, thunkAPI) => {
  try {
    const policy = await AdcmPoliciesApi.createPolicy(arg);
    return policy;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  } finally {
    thunkAPI.dispatch(getPolicies());
  }
});

const updatePolicy = createAsyncThunk(
  'adcm/policiesActions/updatePolicy',
  async ({ policyId, updatedValue }: AdcmPolicyUpdatePayload, thunkAPI) => {
    try {
      const policy = await AdcmPoliciesApi.updatePolicy(policyId, updatedValue);
      return policy;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getPolicies());
    }
  },
);

const deletePolicyWithUpdate = createAsyncThunk(
  'adcm/policiesActions/deletePolicy',
  async (policyId: number, thunkAPI) => {
    try {
      await AdcmPoliciesApi.deletePolicy(policyId);
      await thunkAPI.dispatch(getPolicies());
      thunkAPI.dispatch(showSuccess({ message: 'The policy has been deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    }
  },
);

const loadRoles = createAsyncThunk('adcm/policiesActions/loadRoles', async (arg, thunkAPI) => {
  try {
    const filterParams = {
      type: AdcmRoleType.Role,
    };
    const sortParams: SortParams = {
      sortBy: '',
      sortDirection: 'asc',
    };
    const paginationParams: PaginationParams = {
      pageNumber: 0,
      perPage: 1,
    };
    const batch = await AdcmRolesApi.getRoles(filterParams, sortParams, paginationParams);
    sortParams.sortBy = 'displayName';
    paginationParams.perPage = batch.count;
    return await AdcmRolesApi.getRoles(filterParams, sortParams, paginationParams);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadGroups = createAsyncThunk('adcm/policiesActions/loadGroups', async (arg, thunkAPI) => {
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

const createInitialState = (): AdcmPoliciesActionState => ({
  isAddPolicyDialogOpen: false,
  isCreating: false,
  deleteDialog: {
    id: null,
  },
  editDialog: {
    policy: null,
    roleId: null,
  },
  relatedData: {
    roles: [],
    groups: [],
  },
});

const policiesActionsSlice = createSlice({
  name: 'adcm/policiesActions',
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
    setIsCreating(state, action) {
      state.isCreating = action.payload;
    },
    setEditMode(state, action) {
      state.editDialog.policy = action.payload;
      state.editDialog.roleId = action.payload.role.id;
    },
  },
  extraReducers(builder) {
    builder.addCase(openPoliciesAddDialog.fulfilled, (state) => {
      state.isAddPolicyDialogOpen = true;
    });
    builder.addCase(deletePolicyWithUpdate.pending, (state) => {
      policiesActionsSlice.caseReducers.closeDeleteDialog(state);
    });
    builder.addCase(createPolicy.pending, (state) => {
      state.isAddPolicyDialogOpen = false;
      state.isCreating = true;
    });
    builder.addCase(createPolicy.fulfilled, (state) => {
      state.isCreating = false;
    });
    builder.addCase(createPolicy.rejected, (state) => {
      state.isCreating = false;
    });
    builder.addCase(updatePolicy.pending, (state) => {
      state.isAddPolicyDialogOpen = false;
      state.isCreating = true;
    });
    builder.addCase(updatePolicy.fulfilled, (state) => {
      state.editDialog.policy = null;
      state.editDialog.roleId = null;
      state.isCreating = false;
    });
    builder.addCase(updatePolicy.rejected, (state) => {
      state.editDialog.policy = null;
      state.editDialog.roleId = null;
      state.isCreating = false;
    });
    builder
      .addCase(loadRoles.fulfilled, (state, action) => {
        state.relatedData.roles = action.payload.results;
      })
      .addCase(loadRoles.rejected, (state) => {
        state.relatedData.roles = [];
      })
      .addCase(loadGroups.fulfilled, (state, action) => {
        state.relatedData.groups = action.payload.results;
      })
      .addCase(loadGroups.rejected, (state) => {
        state.relatedData.groups = [];
      });
  },
});

const { openDeleteDialog, closeDeleteDialog, cleanupActions, setEditMode, setIsCreating } =
  policiesActionsSlice.actions;
export {
  createPolicy,
  updatePolicy,
  openPoliciesAddDialog,
  openPoliciesEditDialog,
  deletePolicyWithUpdate,
  openDeleteDialog,
  closeDeleteDialog,
  cleanupActions,
  setEditMode,
  setIsCreating,
};
export default policiesActionsSlice.reducer;
