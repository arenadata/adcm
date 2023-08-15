import { AdcmPoliciesApi, RequestError } from '@api';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { getPolicies } from './policiesSlice';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

interface AdcmPoliciesActionState {
  deleteDialog: {
    id: number | null;
  };
}

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
  },
  extraReducers(builder) {
    builder.addCase(deletePolicyWithUpdate.pending, (state) => {
      policiesActionsSlice.caseReducers.closeDeleteDialog(state);
    });
  },
});

const { openDeleteDialog, closeDeleteDialog } = policiesActionsSlice.actions;
export { deletePolicyWithUpdate, openDeleteDialog, closeDeleteDialog };
export default policiesActionsSlice.reducer;
