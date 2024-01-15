import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostProviderConfigsApi, RequestError } from '@api';
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

type AdcmHostProviderConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
};

type LoadHostProviderConfigurationPayload = {
  hostProviderId: number;
  configId: number;
};

type SaveHostProviderConfigurationPayload = {
  hostProviderId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
};

const createHostProviderConfiguration = createAsyncThunk(
  'adcm/hostProvider/configuration/createHostProviderConfiguration',
  async (
    { hostProviderId, configurationData, attributes, description }: SaveHostProviderConfigurationPayload,
    thunkAPI,
  ) => {
    try {
      const configuration = await AdcmHostProviderConfigsApi.createConfiguration(
        hostProviderId,
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

const createWithUpdateHostProviderConfigurations = createAsyncThunk(
  'adcm/hostProvider/configuration/createAndUpdateHostProviderConfigurations',
  async (arg: SaveHostProviderConfigurationPayload, thunkAPI) => {
    await thunkAPI.dispatch(createHostProviderConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(getHostProviderConfigurationsVersions({ hostProviderId: arg.hostProviderId }));
  },
);

const getHostProviderConfiguration = createAsyncThunk(
  'adcm/hostProvider/configuration/getHostProviderConfiguration',
  async (arg: LoadHostProviderConfigurationPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([
        AdcmHostProviderConfigsApi.getConfig(arg),
        AdcmHostProviderConfigsApi.getConfigSchema(arg),
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

type GetHostProviderConfigurationsPayload = {
  hostProviderId: number;
};

const getHostProviderConfigurationsVersions = createAsyncThunk(
  'adcm/hostProvider/configuration/getHostProviderConfigurationsVersions',
  async ({ hostProviderId }: GetHostProviderConfigurationsPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmHostProviderConfigsApi.getConfigs(hostProviderId);
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

const createInitialState = (): AdcmHostProviderConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const hostProviderConfigurationSlice = createSlice({
  name: 'adcm/hostProvider/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupHostProviderConfiguration() {
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
    builder.addCase(getHostProviderConfiguration.fulfilled, (state, action) => {
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
    builder.addCase(getHostProviderConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getHostProviderConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getHostProviderConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupHostProviderConfiguration, setIsConfigurationLoading, setIsVersionsLoading } =
  hostProviderConfigurationSlice.actions;
export {
  getHostProviderConfiguration,
  getHostProviderConfigurationsVersions,
  cleanupHostProviderConfiguration,
  createWithUpdateHostProviderConfigurations,
};
export default hostProviderConfigurationSlice.reducer;
