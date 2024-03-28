import { createSlice } from '@reduxjs/toolkit';
import { RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmConfigShortView, AdcmConfiguration } from '@models/adcm/configuration';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { ApiRequests } from './entityConfiguration.constants';
import {
  CreateEntityConfigurationArgs,
  LoadEntityConfigurationArgs,
  LoadEntityConfigurationVersionsArgs,
} from './entityConfiguration.types';
import { RequestState } from '@models/loadState';
import { processErrorResponse } from '@utils/responseUtils';

type AdcmEntityConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
  accessCheckStatus: RequestState;
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
    await thunkAPI.dispatch(getConfigurationsVersions(args));
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
      const versions = await requests.getConfigVersions(args);
      return versions;
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

const createInitialState = (): AdcmEntityConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
  accessCheckStatus: RequestState.NotRequested,
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
      state.accessCheckStatus = RequestState.Completed;
    });
    builder.addCase(getConfiguration.pending, (state) => {
      state.accessCheckStatus = RequestState.Pending;
    });
    builder.addCase(getConfiguration.rejected, (state, action) => {
      state.accessCheckStatus = processErrorResponse(action?.payload as RequestError);
      state.loadedConfiguration = null;
    });
    builder.addCase(getConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanup, setIsConfigurationLoading, setIsVersionsLoading } = entityConfigurationSlice.actions;
export { getConfiguration, getConfigurationsVersions, cleanup, createWithUpdateConfigurations };
export default entityConfigurationSlice.reducer;
