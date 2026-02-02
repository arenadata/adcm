import { type AnyAction, type Dispatch, type MiddlewareAPI, createSlice } from '@reduxjs/toolkit';
import type { RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import type { AdcmConfigShortView, AdcmConfiguration } from '@models/adcm/configuration';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { ApiRequests } from './entityConfiguration.constants';
import type {
  CreateEntityConfigurationArgs,
  LoadEntityConfigurationArgs,
  LoadEntityConfigurationVersionsArgs,
  EntityType,
} from './entityConfiguration.types';
import { RequestState } from '@models/loadState';
import { processErrorResponse } from '@utils/responseUtils';
import type { AdcmBackendEvent, Batch, CreateConfigEvent } from '@models/adcm';
import { entityTypeDict } from './entityConfiguration.constants';
import type { AppStore } from '@store/store';

type AdcmEntityConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
  accessCheckStatus: RequestState;
  accessConfigCheckStatus: RequestState;
  isConfigurationUpdated: boolean;
  entity: {
    type?: string;
    [key: string]: string | number | undefined;
  };
};

const createConfiguration = createAsyncThunk(
  'adcm/entityConfiguration/createClusterConfiguration',
  async ({ entityType, args }: CreateEntityConfigurationArgs, thunkAPI) => {
    try {
      const requests = ApiRequests[entityType];
      const config = await requests.createConfig(args);
      return config;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createWithUpdateConfigurations = createAsyncThunk(
  'adcm/entityConfiguration/createWithUpdateConfigurations',
  async (args: CreateEntityConfigurationArgs, thunkAPI) => {
    await thunkAPI.dispatch(createConfiguration(args)).unwrap();
    await thunkAPI.dispatch(getConfigurationsVersions(args as LoadEntityConfigurationVersionsArgs));
  },
);

const createWithUpdateAnsibleSettings = createAsyncThunk(
  'adcm/entityConfiguration/createWithUpdateAnsibleSettings',
  async (args: CreateEntityConfigurationArgs, thunkAPI) => {
    await thunkAPI.dispatch(createConfiguration(args)).unwrap();
    await thunkAPI.dispatch(getConfiguration(args as LoadEntityConfigurationArgs));
  },
);

const getConfiguration = createAsyncThunk(
  'adcm/entityConfiguration/getConfiguration',
  async ({ entityType, args }: LoadEntityConfigurationArgs, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const requests = ApiRequests[entityType];
      const [config, schema] = await Promise.all([requests.getConfig(args), requests.getConfigSchema(args)]);
      return { config, schema };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      executeWithMinDelay({
        startDate,
        delay: defaultSpinnerDelay,
        callback: () => {
          thunkAPI.dispatch(setIsConfigurationLoading(false));
        },
      });
    }
  },
);

const getConfigurationsVersions = createAsyncThunk(
  'adcm/entityConfiguration/getConfigurationsVersions',
  async ({ entityType, args }: LoadEntityConfigurationVersionsArgs, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      const requests = ApiRequests[entityType];
      const versions = requests.getConfigVersions && (await requests.getConfigVersions(args));
      return versions as Batch<AdcmConfigShortView>;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      executeWithMinDelay({
        startDate,
        delay: defaultSpinnerDelay,
        callback: () => {
          thunkAPI.dispatch(setIsVersionsLoading(false));
        },
      });
    }
  },
);

// Mapping from event name to EntityType
const eventToEntityTypeMap: Record<CreateConfigEvent['event'], EntityType> = {
  create_adcm_config: 'settings',
  create_cluster_config: 'cluster',
  create_service_config: 'service',
  create_component_config: 'service-component',
  create_hostprovider_config: 'host-provider',
  create_host_config: 'host',
};

const createConfigrationEventHandle = (
  message: AdcmBackendEvent,
  thunkAPI: MiddlewareAPI<Dispatch<AnyAction>, AppStore>,
) => {
  if (!('event' in message) || !(message.event in eventToEntityTypeMap)) {
    return;
  }

  const configEvent = message as CreateConfigEvent;
  const state = thunkAPI.getState();
  const {
    adcm: {
      entityConfiguration: { entity },
    },
    auth: { username },
  } = state;

  const currentEntityType = entity.type;
  const eventEntityType = eventToEntityTypeMap[configEvent.event];

  if (!eventEntityType || !currentEntityType) {
    return;
  }

  const createdBy = configEvent.object.changes.createdBy;
  if (createdBy === username) {
    return;
  }

  const eventEntityTypeTransformed = entityTypeDict[eventEntityType];

  const isRelevantEvent =
    eventEntityType === 'settings'
      ? currentEntityType === 'settings'
      : currentEntityType === eventEntityTypeTransformed &&
        entity[`${eventEntityTypeTransformed}Id`] === configEvent.object.id;

  if (isRelevantEvent) {
    thunkAPI.dispatch(setIsConfigurationUpdated(true));

    const messageText = `The configuration was updated due to parallel operations. Changed by ${createdBy}`;

    thunkAPI.dispatch(showInfo({ message: messageText }));
  }
};

const createInitialState = (): AdcmEntityConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
  accessCheckStatus: RequestState.NotRequested,
  accessConfigCheckStatus: RequestState.NotRequested,
  isConfigurationUpdated: false,
  entity: {
    type: undefined,
  },
});

const entityConfigurationSlice = createSlice({
  name: 'adcm/entityConfiguration',
  initialState: createInitialState(),
  reducers: {
    cleanup() {
      return createInitialState();
    },
    setIsConfigurationLoading(state, action) {
      state.isConfigurationLoading = action.payload;
    },
    setIsVersionsLoading(state, action) {
      state.isVersionsLoading = action.payload;
    },
    setIsConfigurationUpdated(state, action) {
      state.isConfigurationUpdated = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getConfiguration.fulfilled, (state, action) => {
      const {
        config: { config: configurationData, adcmMeta: attributes },
        schema,
      } = action.payload;
      // https://github.com/microsoft/TypeScript/issues/34933
      // cast to any to avoid compiler warning
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      state.loadedConfiguration = {
        configurationData,
        attributes,
        schema,
      };

      state.isConfigurationLoading = false;
      state.accessConfigCheckStatus = RequestState.Completed;
    });
    builder.addCase(getConfiguration.pending, (state) => {
      state.accessConfigCheckStatus = RequestState.Pending;
    });
    builder.addCase(getConfiguration.rejected, (state, action) => {
      state.accessConfigCheckStatus = processErrorResponse(action?.payload as RequestError);
      state.loadedConfiguration = null;
    });
    builder.addCase(getConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
      state.accessCheckStatus = RequestState.Completed;
      state.isConfigurationUpdated = false;
    });
    builder.addCase(getConfigurationsVersions.pending, (state, action) => {
      state.accessCheckStatus = RequestState.Pending;
      const entityType = entityTypeDict[action.meta.arg.entityType];

      if (entityType === 'settings') {
        state.entity = { type: entityType };
      } else {
        for (const [key, value] of Object.entries(action.meta.arg.args)) {
          if (key === `${entityType}Id`) {
            state.entity = {
              type: entityType,
              [key]: value,
            };
          }
        }
      }
    });
    builder.addCase(getConfigurationsVersions.rejected, (state, action) => {
      state.accessCheckStatus = processErrorResponse(action?.payload as RequestError);
      state.configVersions = [];
      state.entity = { type: undefined };
    });
  },
});

const { cleanup, setIsConfigurationLoading, setIsVersionsLoading, setIsConfigurationUpdated } =
  entityConfigurationSlice.actions;
export {
  getConfiguration,
  getConfigurationsVersions,
  cleanup,
  createWithUpdateConfigurations,
  createWithUpdateAnsibleSettings,
  createConfigrationEventHandle,
  setIsConfigurationUpdated,
};
export default entityConfigurationSlice.reducer;
