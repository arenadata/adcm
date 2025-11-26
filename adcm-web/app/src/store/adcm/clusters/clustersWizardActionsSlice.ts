import { AdcmClustersApi, type RequestError } from '@api';
import type {
  AdcmActionWizardProcess,
  AdcmWizardMappingChangeHistory,
  AdcmWizardProcessOperationPayload,
} from '@models/adcm/wizard';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage, isErrorConflict } from '@utils/httpResponseUtils';
import {
  cleanupClustersWizard,
  getProcess,
  getProcessOnActionClick,
  getStep,
  resetJobDataByStep,
} from './clustersWizardSlice';
import {
  runClusterDynamicAction,
  type RunClusterDynamicActionPayload,
} from '@store/adcm/clusters/clustersDynamicActionsSlice';

interface AdcmCreateProcessPayload {
  clusterId: number;
  actionId: number;
}

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

interface postOperationWithStepResetPayload {
  postOperationPayload: AdcmPostOperationPayload;
  stepId: number;
}

const createProcess = createAsyncThunk(
  'adcm/clustersWizardActions/createProcess',
  async ({ clusterId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClustersApi.createClusterActionWizardProcess(clusterId, actionId);

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

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
      if (isErrorConflict(error as RequestError)) {
        thunkAPI.dispatch(setHasConflictError(true));
      } else {
        thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      }
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

const postOperationWithStepReset = createAsyncThunk(
  'adcm/clustersWizardActions/postOperationWithStepReset',
  async (payload: postOperationWithStepResetPayload, thunkAPI) => {
    thunkAPI.dispatch(setInProgress(true));

    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    thunkAPI.dispatch(resetJobDataByStep(payload.stepId));

    thunkAPI.dispatch(setInProgress(false));
  },
);

const startNewProcess = createAsyncThunk(
  'adcm/clustersWizardActions/startNewProcess',
  async ({ clusterId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClustersApi.createClusterActionWizardProcess(clusterId, actionId);

      thunkAPI.dispatch(getProcess({ clusterId, actionId, processId: process.id }));
      thunkAPI.dispatch(setIsContinueProcessModal(false));
      thunkAPI.dispatch(setBrokenStepError(undefined));

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface AdcmClustersWizardActionsState {
  wizardDialog: {
    process: AdcmActionWizardProcess | null;
    processId: number | null;
    actionId: number | null;
    clusterId: number | null;
    inProgress: boolean;
    hasConflictError: boolean;
    isContinueProcessModal: boolean;
    brokenStepError?: string;
  };
  hostComponentMapDelta?: AdcmWizardMappingChangeHistory;
  selectedStepId?: number;
}

const createInitialState = (): AdcmClustersWizardActionsState => ({
  wizardDialog: {
    process: null,
    processId: null,
    actionId: null,
    clusterId: null,
    inProgress: false,
    hasConflictError: false,
    isContinueProcessModal: false,
    brokenStepError: undefined,
  },
  hostComponentMapDelta: undefined,
  selectedStepId: undefined,
});

const clustersWizardActionsSlice = createSlice({
  name: 'adcm/clustersWizardActions',
  initialState: createInitialState(),
  reducers: {
    cleanupClustersWizardActions() {
      return createInitialState();
    },
    setBrokenStepError(state, action) {
      state.wizardDialog.brokenStepError = action.payload;
    },
    setInProgress(state, action) {
      state.wizardDialog.inProgress = action.payload;
    },
    setSelectedStepId(state, action) {
      state.selectedStepId = action.payload;
    },
    setHostComponentMapDelta(state, action) {
      state.hostComponentMapDelta = action.payload;
    },
    setHasConflictError(state, action) {
      state.wizardDialog.hasConflictError = action.payload;
    },
    setIsContinueProcessModal(state, action) {
      state.wizardDialog.isContinueProcessModal = action.payload;
    },
    resetSelectedStepId(state) {
      state.selectedStepId = undefined;
    },
    openClusterWizardDialog(state, action) {
      state.wizardDialog.processId = action.payload.processId;
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
    builder.addCase(createProcess.fulfilled, (state, action) => {
      state.wizardDialog.process = action.payload;
    });
    builder.addCase(startNewProcess.fulfilled, (state, action) => {
      state.wizardDialog.process = action.payload;
      state.wizardDialog.processId = action.payload.id;
    });
    builder.addCase(postOperation.fulfilled, (state, action) => {
      if (state.wizardDialog.process) {
        state.wizardDialog.process.syncKey = action.payload.syncKey;
      }
      state.selectedStepId = undefined;
    });
    builder.addCase(getProcessOnActionClick.fulfilled, (state, action) => {
      const process = action.payload;
      if (process && process.currentStep !== process.stages[0].steps[0].id) {
        state.wizardDialog.isContinueProcessModal = true;
      }
    });
  },
});

export const {
  cleanupClustersWizardActions,
  openClusterWizardDialog,
  closeClusterWizardDialog,
  setBrokenStepError,
  setHasConflictError,
  setIsContinueProcessModal,
  setSelectedStepId,
  setInProgress,
  setHostComponentMapDelta,
  resetSelectedStepId,
} = clustersWizardActionsSlice.actions;
export {
  createProcess,
  postOperation,
  postOperationWithTask,
  postOperationWithLastStep,
  postOperationWithStepReset,
  startNewProcess,
};

export default clustersWizardActionsSlice.reducer;
