import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostConfigsApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import {
  AdcmConfiguration,
  ConfigurationData,
  ConfigurationAttributes,
  AdcmConfigShortView,
} from '@models/adcm/configuration';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';

interface AdcmHostConfigurationState {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
}

interface LoadHostConfigurationPayload {
  hostId: number;
  configId: number;
}

interface SaveHostConfigurationPayload {
  hostId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

const createHostConfiguration = createAsyncThunk(
  'adcm/host/configuration/createHostConfiguration',
  async ({ hostId, configurationData, attributes, description }: SaveHostConfigurationPayload, thunkAPI) => {
    try {
      const configuration = await AdcmHostConfigsApi.createConfiguration(
        hostId,
        configurationData,
        attributes,
        description,
      );
      return configuration;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createWithUpdateHostsConfigurations = createAsyncThunk(
  'adcm/host/configuration/createWithUpdateHostConfigurations',
  async (arg: SaveHostConfigurationPayload, thunkAPI) => {
    await thunkAPI.dispatch(createHostConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(getHostsConfigurationsVersions(arg.hostId));
  },
);

const getHostsConfiguration = createAsyncThunk(
  'adcm/host/configuration/getHostsConfiguration',
  async (arg: LoadHostConfigurationPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([
        AdcmHostConfigsApi.getConfig(arg),
        AdcmHostConfigsApi.getConfigSchema(arg),
      ]);
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

const getHostsConfigurationsVersions = createAsyncThunk(
  'adcm/host/configuration/getHostsConfigurationsVersions',
  async (hostId: number, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmHostConfigsApi.getConfigs(hostId);
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

const createInitialState = (): AdcmHostConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const hostsConfigurationSlice = createSlice({
  name: 'adcm/host/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupHostsConfiguration() {
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
    builder.addCase(getHostsConfiguration.fulfilled, (state, action) => {
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
    });
    builder.addCase(getHostsConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getHostsConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getHostsConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupHostsConfiguration, setIsConfigurationLoading, setIsVersionsLoading } = hostsConfigurationSlice.actions;
export {
  getHostsConfiguration,
  getHostsConfigurationsVersions,
  cleanupHostsConfiguration,
  createWithUpdateHostsConfigurations,
};
export default hostsConfigurationSlice.reducer;
