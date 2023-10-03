import { AdcmPoliciesApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { getPolicies } from './policiesSlice';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getRoles } from '@store/adcm/roles/rolesSlice';
import { getGroups } from '@store/adcm/groups/groupsSlice';
import { AdcmPolicyPayload } from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';

interface AdcmPoliciesActionState {
  isAddPolicyDialogOpen: boolean;
  isCreating: boolean;
  deleteDialog: {
    id: number | null;
  };
}

const openPoliciesAddDialog = createAsyncThunk('adcm/policiesActions/openPoliciesAddDialog', async (arg, thunkAPI) => {
  try {
    await Promise.all([thunkAPI.dispatch(getRoles()), thunkAPI.dispatch(getGroups())]);
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

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

const deletePolicyWithUpdate = createAsyncThunk(
  'adcm/policiesActions/deletePolicy',
  async (policyId: number, thunkAPI) => {
    try {
      await AdcmPoliciesApi.deletePolicy(policyId);
      await thunkAPI.dispatch(getPolicies());
      thunkAPI.dispatch(showInfo({ message: 'The policy has been deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    }
  },
);

const createInitialState = (): AdcmPoliciesActionState => ({
  isAddPolicyDialogOpen: false,
  isCreating: false,
  deleteDialog: {
    id: null,
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
  },
});

const { openDeleteDialog, closeDeleteDialog, cleanupActions, setIsCreating } = policiesActionsSlice.actions;
export {
  createPolicy,
  openPoliciesAddDialog,
  deletePolicyWithUpdate,
  openDeleteDialog,
  closeDeleteDialog,
  cleanupActions,
  setIsCreating,
};
export default policiesActionsSlice.reducer;
