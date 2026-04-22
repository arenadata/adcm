import type { RequestError } from '@api';
import type { AdcmActionWizardProcess, AdcmWizardMappingChangeHistory } from '@models/adcm/wizard';
import { createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage, isErrorConflict } from '@utils/httpResponseUtils';
import { cleanupEntityWizard, getProcess, getProcessOnActionClick, getStep, resetJobDataByStep } from './wizardSlice';
import { wizardProcessConflictErrorCode } from '@constants';
import type {
  AdcmCreateProcessPayload,
  AdcmPostLastStepOperationPayload,
  AdcmPostOperationPayload,
  AdcmPostTaskOperationPayload,
  PostOperationWithStepResetPayload,
  RunDynamicActionArgs,
  WizardOwnerId,
} from './types/wizardSlice.types';
import { entities } from './constants/wizardSlice.constants';
import { createAsyncThunk } from '@store/redux';

const createProcess = createAsyncThunk(
  'adcm/wizardActions/createProcess',
  async ({ entityArgs, entityType, ...actionArgs }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const entity = entities[entityType];
      const process = await entity.createProcess({ ...entityArgs, ...actionArgs });

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const postOperation = createAsyncThunk(
  'adcm/wizardActions/postOperation',
  async (args: AdcmPostOperationPayload, thunkAPI) => {
    try {
      const { entityType, entityArgs, actionId, processId, operation, actionHostGroupId } = args;

      const entity = entities[entityType];
      const newOperation = await entity.createOperation({
        ...entityArgs,
        actionId,
        processId,
        operation,
        actionHostGroupId,
      });

      await thunkAPI.dispatch(getProcess({ entityType, entityArgs, actionId, processId, actionHostGroupId }));

      return newOperation;
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
  'adcm/wizardActions/postOperationWithTask',
  async (payload: AdcmPostTaskOperationPayload, thunkAPI) => {
    const { postOperationPayload, ...args } = payload;

    // submit step operation
    await thunkAPI.dispatch(postOperation(postOperationPayload)).unwrap();
    // getting task id to get task info
    await thunkAPI.dispatch(getStep(args));
  },
);

const runDynamicAction = createAsyncThunk(
  'adcm/wizardActions/runDynamicAction',
  async ({ entityType, entityArgs, ...args }: RunDynamicActionArgs, thunkAPI) => {
    try {
      const entity = entities[entityType];
      await entity.runDynamicAction({ ...entityArgs, ...args });
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const postOperationWithLastStep = createAsyncThunk(
  'adcm/wizardActions/postOperationWithLastStep',
  async (payload: AdcmPostLastStepOperationPayload, thunkAPI) => {
    // submit step operation
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    // getting task id to get task info
    await thunkAPI.dispatch(runDynamicAction(payload.lastStepPayload));
    thunkAPI.dispatch(cleanupEntityWizard());
    thunkAPI.dispatch(closeWizardDialog());
  },
);

const postOperationWithStepReset = createAsyncThunk(
  'adcm/wizardActions/postOperationWithStepReset',
  async (payload: PostOperationWithStepResetPayload, thunkAPI) => {
    thunkAPI.dispatch(setInProgress(true));

    thunkAPI.dispatch(resetSelectedStepId());
    await thunkAPI.dispatch(postOperation(payload.postOperationPayload));
    thunkAPI.dispatch(resetJobDataByStep(payload.stepId));

    thunkAPI.dispatch(setInProgress(false));
  },
);

const startNewProcess = createAsyncThunk(
  'adcm/wizardActions/startNewProcess',
  async ({ entityType, entityArgs, actionId, actionHostGroupId }: AdcmCreateProcessPayload, thunkAPI) => {
    try {
      const entity = entities[entityType];

      const process = await entity.createProcess({
        ...entityArgs,
        actionHostGroupId,
        actionId,
      });

      await thunkAPI.dispatch(
        getProcess({ entityArgs, entityType, actionId, processId: process.id, actionHostGroupId }),
      );
      thunkAPI.dispatch(setIsContinueProcessModal(false));

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface AdcmWizardActionsState {
  wizardDialog: {
    process: AdcmActionWizardProcess | null;
    processId: number | null;
    actionId: number | null;
    inProgress: boolean;
    hasConflictError: boolean;
    isContinueProcessModal: boolean;
  } & {
    [arg in WizardOwnerId]: number | null;
  };
  hostComponentMapDelta?: AdcmWizardMappingChangeHistory;
  selectedStepId?: number;
}

const createInitialState = (): AdcmWizardActionsState => ({
  wizardDialog: {
    process: null,
    processId: null,
    actionId: null,
    inProgress: false,
    hasConflictError: false,
    isContinueProcessModal: false,
    clusterId: null,
    serviceId: null,
    componentId: null,
  },
  hostComponentMapDelta: undefined,
  selectedStepId: undefined,
});

const wizardActionsSlice = createSlice({
  name: 'adcm/wizardActions',
  initialState: createInitialState(),
  reducers: {
    cleanupWizardActions() {
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
    openWizardDialog(state, action) {
      state.wizardDialog.processId = action.payload.processId;
      state.wizardDialog.actionId = action.payload.actionId;

      const args = action.payload.entityArgs;
      state.wizardDialog.clusterId = args.clusterId;
      state.wizardDialog.serviceId = args.serviceId;
      state.wizardDialog.componentId = args.componentId;
    },
    closeWizardDialog(state) {
      // @ts-ignore
      state.wizardDialog = createInitialState().wizardDialog;
      wizardActionsSlice.caseReducers.resetSelectedStepId(state);
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
  cleanupWizardActions,
  openWizardDialog,
  closeWizardDialog,
  setHasConflictError,
  setIsContinueProcessModal,
  setSelectedStepId,
  setInProgress,
  setHostComponentMapDelta,
  resetSelectedStepId,
} = wizardActionsSlice.actions;
export {
  createProcess,
  postOperation,
  postOperationWithTask,
  postOperationWithLastStep,
  postOperationWithStepReset,
  startNewProcess,
};

export default wizardActionsSlice.reducer;
