import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmJobsApi, type RequestError } from '@api';
import { AdcmClustersApi } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import type {
  AdcmActionProcessOperationStep,
  AdcmActionProcessStep,
  AdcmActionWizardProcess,
} from '@models/adcm/wizard';
import { AdcmWizardStepType } from '@models/adcm/wizard';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import type { AdcmJob, AdcmSubJobDetails, AdcmSubJobLogItem } from '@models/adcm';

interface AdcmGetProcessPayload {
  clusterId: number;
  actionId: number;
  processId: number;
}

interface AdcmGetStepPayload {
  clusterId: number;
  actionId: number;
  processId: number;
  stepId: number;
}

interface AdcmGetStepsPayload {
  clusterId: number;
  actionId: number;
  processId: number;
  stepIds: number[];
}

const addLastStage = (state: AdcmClustersDynamicActionsState) => {
  if (state.process && state.process.stages.length > 0) {
    const allStepIds = state.process.stages.flatMap((stage) => stage.steps.map((step) => step.id));
    const newStepId = Math.max(...allStepIds) + 1;

    if (state.process.currentStep === null) {
      state.process.currentStep = newStepId;
    }

    state.process.stages.push({
      displayName: 'Preparing for running',
      steps: [
        {
          id: newStepId,
          displayName: 'Step 1. Confirmation',
          type: AdcmWizardStepType.LastStep,
          state: state.process.state === 'completed' ? 'completed' : 'created',
        },
      ],
    });
  }
};

const getProcess = createAsyncThunk(
  'adcm/clustersWizard/getProcess',
  async ({ clusterId, actionId, processId }: AdcmGetProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClustersApi.getClusterActionWizardProcess(clusterId, actionId, processId);
      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const refreshProcessStages = createAsyncThunk(
  'adcm/clustersWizard/refreshProcessStages',
  async ({ clusterId, actionId, processId }: AdcmGetProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClustersApi.getClusterActionWizardProcess(clusterId, actionId, processId);
      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getStep = createAsyncThunk(
  'adcm/clustersWizard/getStep',
  async ({ clusterId, actionId, processId, stepId }: AdcmGetStepPayload, thunkAPI) => {
    try {
      const step = await AdcmClustersApi.getClusterActionWizardStep(clusterId, actionId, processId, stepId);
      return step;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getSteps = createAsyncThunk(
  'adcm/clustersWizard/getSteps',
  async ({ clusterId, actionId, processId, stepIds }: AdcmGetStepsPayload, thunkAPI) => {
    try {
      if (stepIds.length === 0) return [];

      const stepPromises = stepIds.map((stepId) =>
        AdcmClustersApi.getClusterActionWizardStep(clusterId, actionId, processId, stepId),
      );
      const steps = await Promise.all(stepPromises);
      return steps;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadJobFromBackend = createAsyncThunk('adcm/clustersWizard/loadJobFromBackend', async (_arg, thunkAPI) => {
  const {
    adcm: {
      clustersWizard: { step },
    },
  } = thunkAPI.getState();

  try {
    if (step) {
      return await AdcmJobsApi.getJob((step as AdcmActionProcessOperationStep).task.id);
    }
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const getJob = createAsyncThunk('adcm/clustersWizard/getJob', async (_arg, thunkAPI) => {
  const startDate = new Date();

  await thunkAPI
    .dispatch(loadJobFromBackend())
    .unwrap()
    .catch(() => {
      thunkAPI.dispatch(showError({ message: 'Job not found' }));
    });

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {},
  });
});

const loadSubJobFromBackend = createAsyncThunk(
  'adcm/clustersWizard/loadSubJobFromBackend',
  async (id: number, thunkAPI) => {
    try {
      const subJob = await AdcmJobsApi.getSubJob(id);
      return subJob;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getSubJob = createAsyncThunk('adcm/clustersWizard/getSubJob', async (id: number, thunkAPI) => {
  await thunkAPI.dispatch(loadSubJobFromBackend(id)).unwrap();
  await thunkAPI.dispatch(getSubJobLog(id));
});

const getSubJobLog = createAsyncThunk('adcm/clustersWizard/getSubJobLog', async (id: number, thunkAPI) => {
  try {
    return await AdcmJobsApi.getSubJobLog(id);
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

type AdcmClustersDynamicActionsState = {
  process: AdcmActionWizardProcess | null;
  step: AdcmActionProcessStep | null;
  steps: AdcmActionProcessStep[];
  job?: AdcmJob;
  subJob?: AdcmSubJobDetails;
  subJobLog: AdcmSubJobLogItem[];
  isLoading: boolean;
};

const createInitialState = (): AdcmClustersDynamicActionsState => ({
  process: null,
  steps: [],
  step: null,
  job: undefined,
  subJob: undefined,
  subJobLog: [],
  isLoading: false,
});

const clustersWizardSlice = createSlice({
  name: 'adcm/clustersWizard',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClustersWizard() {
      return createInitialState();
    },
    resetStep(state) {
      state.step = null;
    },
    resetJobData(state) {
      state.job = undefined;
      state.subJob = undefined;
      state.subJobLog = [];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getProcess.fulfilled, (state, action) => {
      // @ts-ignore
      state.process = action.payload;

      // adding last stage with step, which is will always be shown in map
      // @ts-ignore
      addLastStage(state);
    });
    builder.addCase(getProcess.rejected, (state) => {
      state.process = null;
    });
    builder.addCase(refreshProcessStages.fulfilled, (state, action) => {
      if (state.process) {
        state.process.stages = action.payload.stages;
        state.process.syncKey = action.payload.syncKey;

        // adding last stage with step, which is will always be shown in map
        addLastStage(state);
      }
    });
    builder.addCase(getStep.fulfilled, (state, action) => {
      // @ts-ignore
      state.step = action.payload;
    });
    builder.addCase(getStep.rejected, (state) => {
      state.step = null;
    });
    builder.addCase(getSteps.fulfilled, (state, action) => {
      state.steps = action.payload;
    });
    builder.addCase(getSteps.rejected, (state) => {
      state.steps = [];
    });
    builder.addCase(loadJobFromBackend.fulfilled, (state, action) => {
      state.job = action.payload;
    });
    builder.addCase(loadJobFromBackend.rejected, (state) => {
      state.job = undefined;
    });
    builder.addCase(loadSubJobFromBackend.fulfilled, (state, action) => {
      state.subJob = action.payload;
    });
    builder.addCase(loadSubJobFromBackend.rejected, (state) => {
      state.subJob = undefined;
    });
    builder.addCase(getSubJobLog.fulfilled, (state, action) => {
      state.subJobLog = action.payload;
    });
    builder.addCase(getSubJobLog.rejected, (state) => {
      state.subJobLog = [];
    });
  },
});

export const { cleanupClustersWizard, resetStep, resetJobData } = clustersWizardSlice.actions;
export { getStep, getSteps, getProcess, getJob, getSubJob, getSubJobLog, refreshProcessStages };

export default clustersWizardSlice.reducer;
