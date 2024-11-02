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
import { ModalState } from '@models/modal';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';
import { SortParams } from '@models/table';

interface AdcmPoliciesActionState extends ModalState<AdcmPolicy, 'policy'> {
  createDialog: {
    isOpen: boolean;
  };
  updateDialog: {
    policy: AdcmPolicy | null;
  };
  deleteDialog: {
    policy: AdcmPolicy | null;
  };
  relatedData: {
    roles: AdcmRole[];
    groups: AdcmGroup[];
  };
  isActionInProgress: boolean;
}

const loadRelatedData = createAsyncThunk('adcm/policiesActions/loadRelatedData', async (_, thunkAPI) => {
  try {
    await Promise.all([thunkAPI.dispatch(loadRoles()), thunkAPI.dispatch(loadGroups())]);
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const createPolicyWithUpdate = createAsyncThunk(
  'adcm/policiesActions/createPolicy',
  async (arg: AdcmPolicyPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsActionInProgress(true));
    try {
      const policy = await AdcmPoliciesApi.createPolicy(arg);
      await thunkAPI.dispatch(getPolicies());
      return policy;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setIsActionInProgress(false));
    }
  },
);

const updatePolicyWithUpdate = createAsyncThunk(
  'adcm/policiesActions/updatePolicy',
  async ({ policyId, updatedValue }: AdcmPolicyUpdatePayload, thunkAPI) => {
    thunkAPI.dispatch(setIsActionInProgress(true));
    try {
      const policy = await AdcmPoliciesApi.updatePolicy(policyId, updatedValue);
      await thunkAPI.dispatch(getPolicies());
      return policy;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setIsActionInProgress(false));
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

const sortParams: SortParams = {
  sortBy: 'displayName',
  sortDirection: 'asc',
};

const loadRoles = createAsyncThunk('adcm/policiesActions/loadRoles', async (_, thunkAPI) => {
  try {
    const filterParams = {
      type: AdcmRoleType.Role,
    };
    const { count } = await AdcmRolesApi.getRoles(filterParams, sortParams);
    return await AdcmRolesApi.getRoles(filterParams, sortParams, { pageNumber: 0, perPage: count });
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadGroups = createAsyncThunk('adcm/policiesActions/loadGroups', async (_, thunkAPI) => {
  try {
    const { count } = await AdcmGroupsApi.getGroups({}, sortParams);
    return await AdcmGroupsApi.getGroups({}, sortParams, { pageNumber: 0, perPage: count });
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): AdcmPoliciesActionState => ({
  createDialog: {
    isOpen: false,
  },
  deleteDialog: {
    policy: null,
  },
  updateDialog: {
    policy: null,
  },
  relatedData: {
    roles: [],
    groups: [],
  },
  isActionInProgress: false,
});

const policiesActionsSlice = createCrudSlice({
  name: 'adcm/policiesActions',
  entityName: 'policy',
  createInitialState,
  reducers: {},
  extraReducers(builder) {
    builder.addCase(deletePolicyWithUpdate.pending, (state) => {
      policiesActionsSlice.caseReducers.closeDeleteDialog(state);
    });
    builder.addCase(createPolicyWithUpdate.pending, (state) => {
      policiesActionsSlice.caseReducers.closeCreateDialog(state);
    });
    builder.addCase(updatePolicyWithUpdate.pending, (state) => {
      policiesActionsSlice.caseReducers.closeUpdateDialog(state);
    });
    builder.addCase(updatePolicyWithUpdate.rejected, (state) => {
      state.updateDialog.policy = null;
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

const {
  openCreateDialog,
  openUpdateDialog,
  closeCreateDialog,
  openDeleteDialog,
  closeDeleteDialog,
  closeUpdateDialog,
  setIsActionInProgress,
} = policiesActionsSlice.actions;
export {
  createPolicyWithUpdate as createPolicy,
  updatePolicyWithUpdate as updatePolicy,
  deletePolicyWithUpdate,
  openDeleteDialog,
  closeDeleteDialog,
  loadRelatedData,
  openCreateDialog,
  openUpdateDialog,
  closeUpdateDialog,
  closeCreateDialog,
};
export default policiesActionsSlice.reducer;
