import type {
  AdcmActionWizardProcess,
  AdcmWizardMappingChangeHistory,
  AdcmWizardProcessOperationPayload,
} from '@models/adcm/wizard';
import {
  cleanupClusterServicesWizard,
  getProcess,
  getProcessOnActionClick,
  getStep,
  resetJobDataByStep,
} from '@store/adcm/cluster/services/servicesWizardSlice';
import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage, isErrorConflict } from '@utils/httpResponseUtils';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import {
  runClusterServiceDynamicAction,
  type RunClusterServiceDynamicActionPayload,
} from '@store/adcm/cluster/services/servicesDynamicActionsSlice';
import { wizardProcessConflictErrorCode } from '@constants';

interface AdcmCreateProcessPayload {
  clusterId: number;
  serviceId: number;
  actionId: number;
}

export interface AdcmPostOperationPayload {
  clusterId: number;
  serviceId: number;
  actionId: number;
  processId: number;
  operation: AdcmWizardProcessOperationPayload;
}

interface AdcmPostTaskOperationPayload {
  clusterId: number;
  serviceId: number;
  actionId: number;
  processId: number;
  stepId: number;
  postOperationPayload: AdcmPostOperationPayload;
}

interface AdcmPostLastStepOperationPayload {
  postOperationPayload: AdcmPostOperationPayload;
  lastStepPayload: RunClusterServiceDynamicActionPayload;
}

interface postOperationWithStepResetPayload {
  postOperationPayload: AdcmPostOperationPayload;
  stepId: number;
}

const createProcess = createAsyncThunk(
  'adcm/clusterServicesWizardActions/createProcess',
  async ({ clusterId, serviceId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterServicesApi.createServiceActionWizardProcess(clusterId, serviceId, actionId);

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const postOperation = createAsyncThunk(
  'adcm/clusterServicesWizardActions/postOperation',
  async ({ clusterId, serviceId, actionId, processId, operation }: AdcmPostOperationPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterServicesApi.createServiceActionWizardOperation(
        clusterId,
        serviceId,
        actionId,
        processId,
        operation,
      );

      await thunkAPI.dispatch(getProcess({ clusterId, serviceId, actionId, processId }));

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
  'adcm/clusterServicesWizardActions/postOperationWithTask',
  async (payload: AdcmPostTaskOperationPayload, thunkAPI) => {
    const { clusterId, serviceId, actionId, processId, stepId } = payload;

    // submit step operation
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    // getting task id to get task info
    await thunkAPI.dispatch(getStep({ clusterId, serviceId, actionId, processId, stepId }));
  },
);

const postOperationWithLastStep = createAsyncThunk(
  'adcm/clusterServicesWizardActions/postOperationWithLastStep',
  async (payload: AdcmPostLastStepOperationPayload, thunkAPI) => {
    // submit step operation
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    // getting task id to get task info
    await thunkAPI.dispatch(runClusterServiceDynamicAction(payload.lastStepPayload));
    thunkAPI.dispatch(cleanupClusterServicesWizard());
    thunkAPI.dispatch(closeClusterServiceWizardDialog());
  },
);

const postOperationWithStepReset = createAsyncThunk(
  'adcm/clusterServicesWizardActions/postOperationWithStepReset',
  async (payload: postOperationWithStepResetPayload, thunkAPI) => {
    thunkAPI.dispatch(setInProgress(true));

    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    thunkAPI.dispatch(resetJobDataByStep(payload.stepId));

    thunkAPI.dispatch(setInProgress(false));
  },
);

const startNewProcess = createAsyncThunk(
  'adcm/clusterServicesWizardActions/startNewProcess',
  async ({ clusterId, serviceId, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterServicesApi.createServiceActionWizardProcess(clusterId, serviceId, actionId);

      await thunkAPI.dispatch(getProcess({ clusterId, serviceId, actionId, processId: process.id }));
      thunkAPI.dispatch(setIsContinueProcessModal(false));

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface AdcmServicesWizardActionsState {
  wizardDialog: {
    process: AdcmActionWizardProcess | null;
    processId: number | null;
    actionId: number | null;
    serviceId: number | null;
    clusterId: number | null;
    inProgress: boolean;
    hasConflictError: boolean;
    isContinueProcessModal: boolean;
  };
  hostComponentMapDelta?: AdcmWizardMappingChangeHistory;
  selectedStepId?: number;
}

const createInitialState = (): AdcmServicesWizardActionsState => ({
  wizardDialog: {
    process: null,
    processId: null,
    actionId: null,
    serviceId: null,
    clusterId: null,
    inProgress: false,
    hasConflictError: false,
    isContinueProcessModal: false,
  },
  hostComponentMapDelta: undefined,
  selectedStepId: undefined,
});

const servicesWizardActionsSlice = createSlice({
  name: 'adcm/clusterServicesWizardActions',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterServicesWizardActions() {
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
    openClusterServiceWizardDialog(state, action) {
      state.wizardDialog.processId = action.payload.processId;
      state.wizardDialog.clusterId = action.payload.clusterId;
      state.wizardDialog.serviceId = action.payload.serviceId;
      state.wizardDialog.actionId = action.payload.actionId;
    },
    closeClusterServiceWizardDialog(state) {
      // @ts-ignore
      state.wizardDialog = createInitialState().wizardDialog;
      servicesWizardActionsSlice.caseReducers.resetSelectedStepId(state);
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
  cleanupClusterServicesWizardActions,
  openClusterServiceWizardDialog,
  closeClusterServiceWizardDialog,
  setHasConflictError,
  setIsContinueProcessModal,
  setSelectedStepId,
  setInProgress,
  setHostComponentMapDelta,
  resetSelectedStepId,
} = servicesWizardActionsSlice.actions;
export {
  createProcess,
  postOperation,
  postOperationWithTask,
  postOperationWithLastStep,
  postOperationWithStepReset,
  startNewProcess,
};

export default servicesWizardActionsSlice.reducer;
