import { AdcmClusterMappingApi, AdcmJobsApi, type RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import type { AdcmActionProcessStep, AdcmActionWizardProcess, AdcmWizardJobsData } from '@models/adcm/wizard';
import { AdcmWizardStepType, AdcmWizardStepStates } from '@models/adcm/wizard';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { fulfilledFilter, rejectedFilter } from '@utils/promiseUtils';
import type {
  AdcmHostShortView,
  AdcmJob,
  AdcmMapping,
  AdcmMappingComponent,
  AdcmSubJobDetails,
  AdcmSubJobLogItem,
  NotAddedServicesDictionary,
} from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { LoadState, RequestState } from '@models/loadState';
import { arrayToHash } from '@utils/arrayUtils';
import { isCancelledError } from '@api/httpClient/HttpClient.ts';
import { AbortPayload } from '@constants';

interface AdcmGetProcessPayload {
  clusterId: number;
  serviceId: number;
  actionId: number;
  processId: number;
}

interface AdcmGetStepPayload {
  clusterId: number;
  serviceId: number;
  actionId: number;
  processId: number;
  stepId: number;
}

interface AdcmGetStepsPayload {
  clusterId: number;
  serviceId: number;
  actionId: number;
  processId: number;
  stepIds: number[];
}

let getStepsAbortController: AbortController = new AbortController();

const addLastStage = (state: AdcmServicesWizardState) => {
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
  'adcm/clusterServicesWizard/getProcess',
  async ({ clusterId, serviceId, actionId, processId }: AdcmGetProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterServicesApi.getServiceActionWizardProcess(
        clusterId,
        serviceId,
        actionId,
        processId,
      );
      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getProcessOnActionClick = createAsyncThunk(
  'adcm/clusterServicesWizard/getProcessOnActionClick',
  async ({ clusterId, serviceId, actionId, processId }: AdcmGetProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterServicesApi.getServiceActionWizardProcess(
        clusterId,
        serviceId,
        actionId,
        processId,
      );

      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const refreshProcessStages = createAsyncThunk(
  'adcm/clusterServicesWizard/refreshProcessStages',
  async ({ clusterId, serviceId, actionId, processId }: AdcmGetProcessPayload, thunkAPI) => {
    try {
      const process = await AdcmClusterServicesApi.getServiceActionWizardProcess(
        clusterId,
        serviceId,
        actionId,
        processId,
      );
      return process;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getStep = createAsyncThunk(
  'adcm/clusterServicesWizard/getStep',
  async ({ clusterId, serviceId, actionId, processId, stepId }: AdcmGetStepPayload, thunkAPI) => {
    try {
      const step = await AdcmClusterServicesApi.getServiceActionWizardStep(
        clusterId,
        serviceId,
        actionId,
        processId,
        stepId,
      );
      return step;
    } catch (error) {
      const errorMessage = getErrorMessage(error as RequestError);
      thunkAPI.dispatch(setBrokenStepError(errorMessage));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getSteps = createAsyncThunk(
  'adcm/clusterServicesWizard/getSteps',
  async ({ clusterId, serviceId, actionId, processId, stepIds }: AdcmGetStepsPayload, thunkAPI) => {
    try {
      getStepsAbortController.abort();
      getStepsAbortController = new AbortController();

      if (stepIds.length === 0) return [];

      const stepPromises = stepIds.map((stepId) =>
        AdcmClusterServicesApi.getServiceActionWizardStep(clusterId, serviceId, actionId, processId, stepId, {
          signal: getStepsAbortController.signal,
        }),
      );
      const steps = await Promise.allSettled(stepPromises);

      const isSomeRequestAborted = rejectedFilter(steps).find((request) => isCancelledError(request));
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
  'adcm/clusterServicesWizard/loadJobFromBackend',
  async (arg: loadJobPayload, thunkAPI) => {
    try {
      return await AdcmJobsApi.getJob(arg.jobId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getJob = createAsyncThunk('adcm/clusterServicesWizard/getJob', async (arg: loadJobPayload, thunkAPI) => {
  await thunkAPI.dispatch(loadJobFromBackend(arg));
});

interface loadSubJobLogPayload {
  subJobIds: number[];
  stepId: number;
}

const loadSubJobLogFromBackend = createAsyncThunk(
  'adcm/clusterServicesWizard/loadSubJobLogFromBackend',
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
        throw new Error('All subJobs can not get those logs');
      }

      if (subJobLogs.length < subJobIds.length) {
        throw new Error('Some subJobs can not get those logs');
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

type GetClustersServicesWizardMappingArg = {
  clusterId: number;
};

const loadMappings = createAsyncThunk(
  'adcm/clusterServicesWizard/loadMappings',
  async ({ clusterId }: GetClustersServicesWizardMappingArg, thunkAPI) => {
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
  'adcm/clusterServicesWizard/getMappings',
  async (arg: GetClustersServicesWizardMappingArg, thunkAPI) => {
    await thunkAPI.dispatch(loadMappings(arg));
  },
);

const refreshMapping = createAsyncThunk(
  'adcm/clusterServicesWizard/mapping/refreshMapping',
  async ({ clusterId }: GetClustersServicesWizardMappingArg, _thunkAPI) => {
    const mapping = await AdcmClusterMappingApi.getMapping(clusterId);
    return mapping;
  },
);

const refreshMappingHosts = createAsyncThunk(
  'adcm/clusterServicesWizard/mapping/refreshMappingHosts',
  async ({ clusterId }: GetClustersServicesWizardMappingArg, _thunkAPI) => {
    const hosts = await AdcmClusterMappingApi.getMappingHosts(clusterId);
    return hosts;
  },
);

const refreshMappingComponents = createAsyncThunk(
  'adcm/clusterServicesWizard/mapping/refreshMappingComponents',
  async ({ clusterId }: GetClustersServicesWizardMappingArg, _thunkAPI) => {
    const components = await AdcmClusterMappingApi.getMappingComponents(clusterId);
    return components;
  },
);

type AdcmServicesWizardState = {
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

const createInitialState = (): AdcmServicesWizardState => ({
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

const clusterServicesWizardSlice = createSlice({
  name: 'adcm/clusterServicesWizard',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterServicesWizard() {
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

      const index = state.steps.findIndex((step) => step.id === action.payload.id);
      if (index !== -1) {
        // @ts-ignore
        state.steps[index] = action.payload;
      }
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
  cleanupClusterServicesWizard,
  openRequiredServicesDialog,
  closeRequiredServicesDialog,
  setBrokenStepError,
  resetStep,
  resetJobData,
  resetJobDataByStep,
} = clusterServicesWizardSlice.actions;
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

export default clusterServicesWizardSlice.reducer;
