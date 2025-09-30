import { AdcmClustersApi, type RequestError } from '@api';
import type { AdcmActionWizardProcess, AdcmWizardProcessOperationPayload } from '@models/adcm/wizard';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { cleanupClustersWizard, getProcess, getStep } from '@store/adcm/clusters/clustersWizardSlice';
import {
  runClusterDynamicAction,
  type RunClusterDynamicActionPayload,
} from '@store/adcm/clusters/clustersDynamicActionsSlice';

export interface AdcmPostOperationPayload {
  clusterId: number;
  actionId: number;
  processId: number;
  operation: AdcmWizardProcessOperationPayload;
}

interface AdcmPostTaskOperationPayload {
  clusterId: number;
  actionId: number;
  processId: number;
  stepId: number;
  postOperationPayload: AdcmPostOperationPayload;
}

interface AdcmPostLastStepOperationPayload {
  postOperationPayload: AdcmPostOperationPayload;
  lastStepPayload: RunClusterDynamicActionPayload;
}

const postOperation = createAsyncThunk(
  'adcm/clustersWizardActions/postOperation',
  async ({ clusterId, actionId, processId, operation }: AdcmPostOperationPayload, thunkAPI) => {
    try {
      const process = await AdcmClustersApi.createClusterActionWizardOperation(
        clusterId,
        actionId,
        processId,
        operation,
      );

      await thunkAPI.dispatch(getProcess({ clusterId, actionId, processId }));

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const postOperationWithTask = createAsyncThunk(
  'adcm/clustersWizardActions/postOperationWithTask',
  async (payload: AdcmPostTaskOperationPayload, thunkAPI) => {
    const { clusterId, actionId, processId, stepId } = payload;

    // submit step operation
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    // getting task id to get task info
    await thunkAPI.dispatch(getStep({ clusterId, actionId, processId, stepId }));
  },
);

const postOperationWithLastStep = createAsyncThunk(
  'adcm/clustersWizardActions/postOperationWithLastStep',
  async (payload: AdcmPostLastStepOperationPayload, thunkAPI) => {
    // submit step operation
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    // getting task id to get task info
    await thunkAPI.dispatch(runClusterDynamicAction(payload.lastStepPayload));
    thunkAPI.dispatch(cleanupClustersWizard());
    thunkAPI.dispatch(closeClusterWizardDialog());
  },
);

interface AdcmClustersWizardActionsState {
  wizardDialog: {
    process: AdcmActionWizardProcess | null;
    actionId: number | null;
    clusterId: number | null;
  };
  selectedStepId?: number;
}

const createInitialState = (): AdcmClustersWizardActionsState => ({
  wizardDialog: {
    process: null,
    actionId: null,
    clusterId: null,
  },
  selectedStepId: undefined,
});

const clustersWizardActionsSlice = createSlice({
  name: 'adcm/clustersWizardActions',
  initialState: createInitialState(),
  reducers: {
    cleanupClustersWizardActions() {
      return createInitialState();
    },
    setSelectedStepId(state, action) {
      state.selectedStepId = action.payload;
    },
    resetSelectedStepId(state) {
      state.selectedStepId = undefined;
    },
    openClusterWizardDialog(state, action) {
      state.wizardDialog.process = action.payload.process;
      state.wizardDialog.clusterId = action.payload.clusterId;
      state.wizardDialog.actionId = action.payload.actionId;
    },
    closeClusterWizardDialog(state) {
      // @ts-ignore
      state.wizardDialog = createInitialState().wizardDialog;
      clustersWizardActionsSlice.caseReducers.resetSelectedStepId(state);
    },
  },
  extraReducers: (builder) => {
    builder.addCase(postOperation.fulfilled, (state, action) => {
      if (state.wizardDialog.process) {
        state.wizardDialog.process.syncKey = action.payload.syncKey;
      }
      state.selectedStepId = undefined;
    });
  },
});

export const {
  cleanupClustersWizardActions,
  openClusterWizardDialog,
  closeClusterWizardDialog,
  setSelectedStepId,
  resetSelectedStepId,
} = clustersWizardActionsSlice.actions;
export { postOperation, postOperationWithTask, postOperationWithLastStep };

export default clustersWizardActionsSlice.reducer;
