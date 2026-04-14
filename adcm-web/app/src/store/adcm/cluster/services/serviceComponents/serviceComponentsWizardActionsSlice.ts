import type {
  AdcmActionWizardProcess,
  AdcmWizardMappingChangeHistory,
  AdcmWizardProcessOperationPayload,
} from '@models/adcm/wizard';
import { createAsyncThunk } from '@store/redux';
import { AdcmClusterServiceComponentsApi, type RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage, isErrorConflict } from '@utils/httpResponseUtils';
import { createSlice } from '@reduxjs/toolkit';
import {
  cleanupClusterServiceComponentsWizard,
  getProcess,
  getProcessOnActionClick,
  getStep,
  resetJobDataByStep,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsWizardSlice';
import {
  runClusterServiceComponentDynamicAction,
  type RunClusterServiceComponentDynamicActionPayload,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsDynamicActionsSlice';
import { wizardProcessConflictErrorCode } from '@constants';

interface AdcmCreateProcessPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionId: number;
}

export interface AdcmPostOperationPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionId: number;
  processId: number;
  operation: AdcmWizardProcessOperationPayload;
}

interface AdcmPostTaskOperationPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
  actionId: number;
  processId: number;
  stepId: number;
  postOperationPayload: AdcmPostOperationPayload;
}

interface AdcmPostLastStepOperationPayload {
  postOperationPayload: AdcmPostOperationPayload;
  lastStepPayload: RunClusterServiceComponentDynamicActionPayload;
}

interface postOperationWithStepResetPayload {
  postOperationPayload: AdcmPostOperationPayload;
  stepId: number;
}

const createProcess = createAsyncThunk(
  'adcm/clusterServiceComponentsWizardActions/createProcess',
  async ({ clusterId, serviceId, componentId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterServiceComponentsApi.createClusterServiceComponentActionWizardProcess(
        clusterId,
        serviceId,
        componentId,
        actionId,
      );

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const postOperation = createAsyncThunk(
  'adcm/clusterServiceComponentsWizardActions/postOperation',
  async ({ clusterId, serviceId, componentId, actionId, processId, operation }: AdcmPostOperationPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterServiceComponentsApi.createClusterServiceComponentActionWizardOperation(
        clusterId,
        serviceId,
        componentId,
        actionId,
        processId,
        operation,
      );

      await thunkAPI.dispatch(getProcess({ clusterId, serviceId, componentId, actionId, processId }));

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
  'adcm/clusterServiceComponentsWizardActions/postOperationWithTask',
  async (payload: AdcmPostTaskOperationPayload, thunkAPI) => {
    const { clusterId, serviceId, componentId, actionId, processId, stepId } = payload;

    // submit step operation
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    // getting task id to get task info
    await thunkAPI.dispatch(getStep({ clusterId, serviceId, componentId, actionId, processId, stepId }));
  },
);

const postOperationWithLastStep = createAsyncThunk(
  'adcm/clusterServiceComponentsWizardActions/postOperationWithLastStep',
  async (payload: AdcmPostLastStepOperationPayload, thunkAPI) => {
    // submit step operation
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    // getting task id to get task info
    await thunkAPI.dispatch(runClusterServiceComponentDynamicAction(payload.lastStepPayload));
    thunkAPI.dispatch(cleanupClusterServiceComponentsWizard());
    thunkAPI.dispatch(closeClusterServiceComponentsWizardDialog());
  },
);

const postOperationWithStepReset = createAsyncThunk(
  'adcm/clusterServiceComponentsWizardActions/postOperationWithStepReset',
  async (payload: postOperationWithStepResetPayload, thunkAPI) => {
    thunkAPI.dispatch(setInProgress(true));

    thunkAPI.dispatch(resetSelectedStepId());
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    thunkAPI.dispatch(resetJobDataByStep(payload.stepId));

    thunkAPI.dispatch(setInProgress(false));
  },
);

const startNewProcess = createAsyncThunk(
  'adcm/clusterServiceComponentsWizardActions/startNewProcess',
  async ({ clusterId, serviceId, componentId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterServiceComponentsApi.createClusterServiceComponentActionWizardProcess(
        clusterId,
        serviceId,
        componentId,
        actionId,
      );

      await thunkAPI.dispatch(getProcess({ clusterId, serviceId, componentId, actionId, processId: process.id }));
      thunkAPI.dispatch(setIsContinueProcessModal(false));

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface AdcmServiceComponentsWizardActionsState {
  wizardDialog: {
    process: AdcmActionWizardProcess | null;
    processId: number | null;
    actionId: number | null;
    serviceId: number | null;
    componentId: number | null;
    clusterId: number | null;
    inProgress: boolean;
    hasConflictError: boolean;
    isContinueProcessModal: boolean;
  };
  hostComponentMapDelta?: AdcmWizardMappingChangeHistory;
  selectedStepId?: number;
}

const createInitialState = (): AdcmServiceComponentsWizardActionsState => ({
  wizardDialog: {
    process: null,
    processId: null,
    actionId: null,
    serviceId: null,
    componentId: null,
    clusterId: null,
    inProgress: false,
    hasConflictError: false,
    isContinueProcessModal: false,
  },
  hostComponentMapDelta: undefined,
  selectedStepId: undefined,
});

const serviceComponentsWizardActionsSlice = createSlice({
  name: 'adcm/clusterServiceComponentsWizardActions',
  initialState: createInitialState(),
  reducers: {
    cleanupServiceComponentsWizardActions() {
      return createInitialState();
    },
    setInProgress(state, action) {
      state.wizardDialog.inProgress = action.payload;
    },
    setSelectedStepId(state, action) {
      state.selectedStepId = action.payload;
    },
    resetSelectedStepId(state) {
      state.selectedStepId = undefined;
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
    openClusterServiceComponentsWizardDialog(state, action) {
      state.wizardDialog.processId = action.payload.processId;
      state.wizardDialog.clusterId = action.payload.clusterId;
      state.wizardDialog.serviceId = action.payload.serviceId;
      state.wizardDialog.componentId = action.payload.componentId;
      state.wizardDialog.actionId = action.payload.actionId;
    },
    closeClusterServiceComponentsWizardDialog(state) {
      // @ts-ignore
      state.wizardDialog = createInitialState().wizardDialog;
      serviceComponentsWizardActionsSlice.caseReducers.resetSelectedStepId(state);
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
  cleanupServiceComponentsWizardActions,
  openClusterServiceComponentsWizardDialog,
  closeClusterServiceComponentsWizardDialog,
  setHasConflictError,
  setIsContinueProcessModal,
  setSelectedStepId,
  setInProgress,
  setHostComponentMapDelta,
  resetSelectedStepId,
} = serviceComponentsWizardActionsSlice.actions;
export {
  createProcess,
  postOperation,
  postOperationWithTask,
  postOperationWithLastStep,
  postOperationWithStepReset,
  startNewProcess,
};

export default serviceComponentsWizardActionsSlice.reducer;
