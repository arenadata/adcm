import type {
  AdcmActionWizardProcess,
  AdcmWizardMappingChangeHistory,
  AdcmWizardProcessOperationPayload,
} from '@models/adcm/wizard';
import {
  cleanupClusterHostsWizard,
  getProcess,
  getProcessOnActionClick,
  getStep,
  resetJobDataByStep,
} from '@store/adcm/cluster/hosts/hostsWizardSlice';
import { createAsyncThunk } from '@store/redux';
import { AdcmClusterHostsApi, type RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage, isErrorConflict } from '@utils/httpResponseUtils';
import { createSlice } from '@reduxjs/toolkit';
import {
  runClusterHostDynamicAction,
  type RunClusterHostDynamicActionPayload,
} from '@store/adcm/cluster/hosts/hostsDynamicActionsSlice';
import { wizardProcessConflictErrorCode } from '@constants';

interface AdcmCreateProcessPayload {
  clusterId: number;
  hostId: number;
  actionId: number;
}

export interface AdcmPostOperationPayload {
  clusterId: number;
  hostId: number;
  actionId: number;
  processId: number;
  operation: AdcmWizardProcessOperationPayload;
}

interface AdcmPostTaskOperationPayload {
  clusterId: number;
  hostId: number;
  actionId: number;
  processId: number;
  stepId: number;
  postOperationPayload: AdcmPostOperationPayload;
}

interface AdcmPostLastStepOperationPayload {
  postOperationPayload: AdcmPostOperationPayload;
  lastStepPayload: RunClusterHostDynamicActionPayload;
}

interface postOperationWithStepResetPayload {
  postOperationPayload: AdcmPostOperationPayload;
  stepId: number;
}

const createProcess = createAsyncThunk(
  'adcm/clusterHostsWizardActions/createProcess',
  async ({ clusterId, hostId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterHostsApi.createHostActionWizardProcess(clusterId, hostId, actionId);

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const postOperation = createAsyncThunk(
  'adcm/clusterHostsWizardActions/postOperation',
  async ({ clusterId, hostId, actionId, processId, operation }: AdcmPostOperationPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterHostsApi.createHostActionWizardOperation(
        clusterId,
        hostId,
        actionId,
        processId,
        operation,
      );

      await thunkAPI.dispatch(getProcess({ clusterId, hostId, actionId, processId }));

      return process;
    } catch (error) {
      if (isErrorConflict(error as RequestError, wizardProcessConflictErrorCode)) {
        thunkAPI.dispatch(setHasConflictError(true));
      } else {
        thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      }
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const postOperationWithTask = createAsyncThunk(
  'adcm/clusterHostsWizardActions/postOperationWithTask',
  async (payload: AdcmPostTaskOperationPayload, thunkAPI) => {
    const { clusterId, hostId, actionId, processId, stepId } = payload;

    // submit step operation
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    // getting task id to get task info
    await thunkAPI.dispatch(getStep({ clusterId, hostId, actionId, processId, stepId }));
  },
);

const postOperationWithLastStep = createAsyncThunk(
  'adcm/clusterHostsWizardActions/postOperationWithLastStep',
  async (payload: AdcmPostLastStepOperationPayload, thunkAPI) => {
    // submit step operation
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    // getting task id to get task info
    await thunkAPI.dispatch(runClusterHostDynamicAction(payload.lastStepPayload));
    thunkAPI.dispatch(cleanupClusterHostsWizard());
    thunkAPI.dispatch(closeClusterHostsWizardDialog());
  },
);

const postOperationWithStepReset = createAsyncThunk(
  'adcm/clusterHostsWizardActions/postOperationWithStepReset',
  async (payload: postOperationWithStepResetPayload, thunkAPI) => {
    thunkAPI.dispatch(setInProgress(true));

    thunkAPI.dispatch(resetSelectedStepId());
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    thunkAPI.dispatch(resetJobDataByStep(payload.stepId));

    thunkAPI.dispatch(setInProgress(false));
  },
);

const startNewProcess = createAsyncThunk(
  'adcm/clusterHostsWizardActions/startNewProcess',
  async ({ clusterId, hostId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterHostsApi.createHostActionWizardProcess(clusterId, hostId, actionId);

      await thunkAPI.dispatch(getProcess({ clusterId, hostId, actionId, processId: process.id }));
      thunkAPI.dispatch(setIsContinueProcessModal(false));

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface AdcmHostsWizardActionsState {
  wizardDialog: {
    process: AdcmActionWizardProcess | null;
    processId: number | null;
    actionId: number | null;
    hostId: number | null;
    clusterId: number | null;
    inProgress: boolean;
    hasConflictError: boolean;
    isContinueProcessModal: boolean;
  };
  hostComponentMapDelta?: AdcmWizardMappingChangeHistory;
  selectedStepId?: number;
}

const createInitialState = (): AdcmHostsWizardActionsState => ({
  wizardDialog: {
    process: null,
    processId: null,
    actionId: null,
    hostId: null,
    clusterId: null,
    inProgress: false,
    hasConflictError: false,
    isContinueProcessModal: false,
  },
  hostComponentMapDelta: undefined,
  selectedStepId: undefined,
});

const clusterHostsWizardActionsSlice = createSlice({
  name: 'adcm/clusterHostsWizardActions',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterHostsWizardActions() {
      return createInitialState();
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
    openClusterHostsWizardDialog(state, action) {
      state.wizardDialog.processId = action.payload.processId;
      state.wizardDialog.hostId = action.payload.hostId;
      state.wizardDialog.clusterId = action.payload.clusterId;
      state.wizardDialog.actionId = action.payload.actionId;
    },
    closeClusterHostsWizardDialog(state) {
      // @ts-ignore
      state.wizardDialog = createInitialState().wizardDialog;
      clusterHostsWizardActionsSlice.caseReducers.resetSelectedStepId(state);
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
  cleanupClusterHostsWizardActions,
  openClusterHostsWizardDialog,
  closeClusterHostsWizardDialog,
  setHasConflictError,
  setIsContinueProcessModal,
  setSelectedStepId,
  setInProgress,
  setHostComponentMapDelta,
  resetSelectedStepId,
} = clusterHostsWizardActionsSlice.actions;
export {
  createProcess,
  postOperation,
  postOperationWithTask,
  postOperationWithLastStep,
  postOperationWithStepReset,
  startNewProcess,
};

export default clusterHostsWizardActionsSlice.reducer;
