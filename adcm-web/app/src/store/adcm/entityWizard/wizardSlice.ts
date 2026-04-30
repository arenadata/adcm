import { type RequestError, AdcmJobsApi, AdcmClusterMappingApi } from '@api';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import type {
  AdcmMapping,
  AdcmHostShortView,
  AdcmMappingComponent,
  NotAddedServicesDictionary,
  AdcmJob,
  AdcmSubJobDetails,
  AdcmSubJobLogItem,
} from '@models/adcm';
import {
  type AdcmActionWizardProcess,
  type AdcmActionProcessStep,
  type AdcmWizardJobsData,
  AdcmWizardStepStates,
  AdcmWizardStepType,
} from '@models/adcm/wizard';
import { LoadState, RequestState } from '@models/loadState';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { arrayToHash } from '@utils/arrayUtils';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { fulfilledFilter, rejectedFilter } from '@utils/promiseUtils';
import { entities } from './constants/wizardSlice.constants';
import type { AdcmGetProcessPayload, AdcmGetStepPayload, AdcmGetStepsPayload } from './types/wizardSlice.types';
import { isCancelledError } from '@api/httpClient/HttpClient';
import { AbortPayload } from '@constants';

let getStepsAbortController: AbortController = new AbortController();

const addLastStage = (state: AdcmEntityWizardState) => {
  if (state.process && state.process.stages.length > 0) {
    const allStepIds = state.process.stages.flatMap((stage) => stage.steps.map((step) => step.id));
    const newStepId = Math.max(...allStepIds) + 1;

    if (state.process.currentStep === null) {
      state.process.currentStep = newStepId;
    }

    state.process.stages.push({
      displayName: 'Preparing for running',
      description: '',
      steps: [
        {
          id: newStepId,
          displayName: 'Step 1. Confirmation',
          description: '',
          required: true,
          type: AdcmWizardStepType.LastStep,
          state:
            state.process.state === AdcmWizardStepStates.Completed
              ? AdcmWizardStepStates.Completed
              : AdcmWizardStepStates.Created,
        },
      ],
    });
  }
};

const getProcess = createAsyncThunk(
  'adcm/entityWizard/getProcess',
  async ({ entityType, entityArgs, ...rest }: AdcmGetProcessPayload, thunkAPI) => {
    try {
      const entity = entities[entityType];

      const process = await entity.getProcess({ ...entityArgs, ...rest });
      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getProcessOnActionClick = createAsyncThunk(
  'adcm/entityWizard/getProcessOnActionClick',
  async ({ entityType, entityArgs, ...rest }: AdcmGetProcessPayload, thunkAPI) => {
    try {
      const entity = entities[entityType];

      const process = await entity.getProcess({ ...entityArgs, ...rest });
      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const refreshProcessStages = createAsyncThunk(
  'adcm/entityWizard/refreshProcessStages',
  async ({ entityType, entityArgs, ...rest }: AdcmGetProcessPayload, thunkAPI) => {
    try {
      const entity = entities[entityType];

      const process = await entity.getProcess({ ...entityArgs, ...rest });
      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getStep = createAsyncThunk(
  'adcm/entityWizard/getStep',
  async ({ entityType, entityArgs, ...actionArgs }: AdcmGetStepPayload, thunkAPI) => {
    try {
      const entity = entities[entityType];
      const step = await entity.getStep({ ...entityArgs, ...actionArgs });

      return step;
    } catch (error) {
      const errorMessage = getErrorMessage(error as RequestError);
      thunkAPI.dispatch(setBrokenStepError(errorMessage));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getSteps = createAsyncThunk(
  'adcm/entityWizard/getSteps',
  async ({ entityType, entityArgs, stepIds, ...actionArgs }: AdcmGetStepsPayload, thunkAPI) => {
    try {
      getStepsAbortController.abort();
      getStepsAbortController = new AbortController();

      if (stepIds.length === 0) return [];

      const stepPromises = stepIds.map((stepId) =>
        thunkAPI.dispatch(getStep({ entityType, entityArgs, stepId, ...actionArgs })).unwrap(),
      );
      const steps = await Promise.allSettled(stepPromises);

      const isSomeRequestAborted = rejectedFilter(steps).some((request) => isCancelledError(request));
      if (isSomeRequestAborted) {
        return thunkAPI.rejectWithValue(AbortPayload);
      }

      return fulfilledFilter(steps);
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface loadJobPayload {
  jobId: number;
  stepId: number;
}

const loadJobFromBackend = createAsyncThunk(
  'adcm/entityWizard/loadJobFromBackend',
  async (arg: loadJobPayload, thunkAPI) => {
    try {
      return await AdcmJobsApi.getJob(arg.jobId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getJob = createAsyncThunk('adcm/entityWizard/getJob', async (arg: loadJobPayload, thunkAPI) => {
  await thunkAPI.dispatch(loadJobFromBackend(arg));
});

interface loadSubJobLogPayload {
  subJobIds: number[];
  stepId: number;
}

const loadSubJobLogFromBackend = createAsyncThunk(
  'adcm/entityWizard/loadSubJobLogFromBackend',
  async (arg: loadSubJobLogPayload, thunkAPI) => {
    const { subJobIds } = arg;
    try {
      const subJobLogPromises = await Promise.allSettled(
        arg.subJobIds.map(async (subJobId) => ({
          subJobId,
          subJobLogs: await AdcmJobsApi.getSubJobLog(subJobId),
        })),
      );
      const subJobLogs = fulfilledFilter(subJobLogPromises);
      if (subJobLogs.length === 0 && subJobIds.length > 0) {
        throw new Error('All subJobs cannot get those logs');
      }

      if (subJobLogs.length < subJobIds.length) {
        throw new Error('Some subJobs cannot get those logs');
      }

      return subJobLogs.reduce(
        (res, { subJobId, subJobLogs }) => {
          res[subJobId] = subJobLogs;

          return res;
        },
        {} as Record<AdcmSubJobDetails['id'], AdcmSubJobLogItem[]>,
      );
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

type GetentityWizardMappingArg = {
  clusterId: number;
};

const loadMappings = createAsyncThunk(
  'adcm/entityWizard/loadMappings',
  async ({ clusterId }: GetentityWizardMappingArg, thunkAPI) => {
    try {
      const mapping = await AdcmClusterMappingApi.getMapping(clusterId);
      const hosts = await AdcmClusterMappingApi.getMappingHosts(clusterId);
      const components = await AdcmClusterMappingApi.getMappingComponents(clusterId);
      const notAddedServices = await AdcmClusterServicesApi.getClusterServiceCandidates(clusterId);
      return { mapping, components, hosts, notAddedServices };
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getMappings = createAsyncThunk(
  'adcm/entityWizard/getMappings',
  async (arg: GetentityWizardMappingArg, thunkAPI) => {
    await thunkAPI.dispatch(loadMappings(arg));
  },
);

const refreshMapping = createAsyncThunk(
  'adcm/entityWizard/mapping/refreshMapping',
  async ({ clusterId }: GetentityWizardMappingArg, _thunkAPI) => {
    const mapping = await AdcmClusterMappingApi.getMapping(clusterId);
    return mapping;
  },
);

const refreshMappingHosts = createAsyncThunk(
  'adcm/entityWizard/mapping/refreshMappingHosts',
  async ({ clusterId }: GetentityWizardMappingArg, _thunkAPI) => {
    const hosts = await AdcmClusterMappingApi.getMappingHosts(clusterId);
    return hosts;
  },
);

const refreshMappingComponents = createAsyncThunk(
  'adcm/entityWizard/mapping/refreshMappingComponents',
  async ({ clusterId }: GetentityWizardMappingArg, _thunkAPI) => {
    const components = await AdcmClusterMappingApi.getMappingComponents(clusterId);
    return components;
  },
);

type AdcmEntityWizardState = {
  process: AdcmActionWizardProcess | null;
  step: AdcmActionProcessStep | null;
  steps: AdcmActionProcessStep[];
  jobsData: AdcmWizardJobsData;
  mapping: {
    mapping: AdcmMapping[];
    hosts: AdcmHostShortView[];
    components: AdcmMappingComponent[];
    loadState: LoadState;
    notAddedServicesDictionary: NotAddedServicesDictionary;
    requiredServicesDialog: {
      component: AdcmMappingComponent | null;
    };
    accessCheckStatus: RequestState;
  };
  brokenStepError?: string;
  isLoading: boolean;
};

const createInitialState = (): AdcmEntityWizardState => ({
  process: null,
  steps: [],
  step: null,
  jobsData: {},
  mapping: {
    mapping: [],
    hosts: [],
    components: [],
    loadState: LoadState.NotLoaded,
    notAddedServicesDictionary: {},
    requiredServicesDialog: {
      component: null,
    },
    accessCheckStatus: RequestState.NotRequested,
  },
  brokenStepError: undefined,
  isLoading: false,
});

const entityWizardSlice = createSlice({
  name: 'adcm/entityWizard',
  initialState: createInitialState(),
  reducers: {
    cleanupEntityWizard() {
      return createInitialState();
    },
    openRequiredServicesDialog(state, action) {
      state.mapping.requiredServicesDialog.component = action.payload;
    },
    closeRequiredServicesDialog(state) {
      state.mapping.requiredServicesDialog.component = null;
    },
    setBrokenStepError(state, action) {
      state.brokenStepError = action.payload;
    },
    resetStep(state) {
      state.step = null;
    },
    resetJobData(state) {
      state.jobsData = {};
    },
    resetJobDataByStep(state, action) {
      state.jobsData = Object.fromEntries(
        Object.entries(state.jobsData).filter(([stepId]) => Number(stepId) < action.payload),
      );
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
    builder.addCase(getProcessOnActionClick.fulfilled, (state, action) => {
      // @ts-ignore
      state.process = action.payload;

      // adding last stage with step, which is will always be shown in map
      // @ts-ignore
      addLastStage(state);
    });
    builder.addCase(getProcessOnActionClick.rejected, (state) => {
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
    builder.addCase(getSteps.rejected, (state, action) => {
      if (action.payload !== AbortPayload) {
        state.steps = [];
      }
    });
    builder.addCase(loadJobFromBackend.fulfilled, (state, action) => {
      const id = action.meta.arg.stepId;
      if (id) {
        if (!state.jobsData[id]) {
          state.jobsData[id] = { job: {} as AdcmJob };
        }
        state.jobsData[id].job = action.payload;
      }
    });
    builder.addCase(loadJobFromBackend.rejected, (state, action) => {
      const id = action.meta.arg.stepId;
      if (id && state.jobsData[id]) {
        state.jobsData[id].job = undefined;
      }
    });
    builder.addCase(loadSubJobLogFromBackend.fulfilled, (state, action) => {
      const id = action.meta.arg.stepId;
      if (id) {
        const job = state.jobsData[id] ?? (state.jobsData[id] = {});
        job.subJobLog = action.payload;
      }
    });
    builder.addCase(loadSubJobLogFromBackend.rejected, (state, action) => {
      const id = state.step?.id;
      if (id) {
        const job = state.jobsData[id] ?? (state.jobsData[id] = {});
        const subJobLog = job.subJobLog ?? (job.subJobLog = {});
        action.meta.arg.subJobIds.map((id) => delete subJobLog[id]);
      }
    });
    builder.addCase(loadMappings.fulfilled, (state, action) => {
      state.mapping.mapping = action.payload.mapping;
      state.mapping.hosts = action.payload.hosts;
      state.mapping.components = action.payload.components;
      state.mapping.notAddedServicesDictionary = arrayToHash(action.payload.notAddedServices, (s) => s.id);
    });
    builder.addCase(getMappings.pending, (state) => {
      state.mapping.loadState = LoadState.Loading;
    });
    builder.addCase(getMappings.fulfilled, (state) => {
      state.mapping.loadState = LoadState.Loaded;
    });
    builder.addCase(refreshMapping.fulfilled, (state, action) => {
      state.mapping.mapping = action.payload;
    });
    builder.addCase(refreshMappingHosts.fulfilled, (state, action) => {
      state.mapping.hosts = action.payload;
    });
    builder.addCase(refreshMappingComponents.fulfilled, (state, action) => {
      state.mapping.components = action.payload;
    });
  },
});

export const {
  cleanupEntityWizard,
  openRequiredServicesDialog,
  closeRequiredServicesDialog,
  setBrokenStepError,
  resetStep,
  resetJobData,
  resetJobDataByStep,
} = entityWizardSlice.actions;
export {
  getStep,
  getSteps,
  getProcess,
  getJob,
  getProcessOnActionClick,
  loadSubJobLogFromBackend,
  refreshProcessStages,
  getMappings,
};

export default entityWizardSlice.reducer;
