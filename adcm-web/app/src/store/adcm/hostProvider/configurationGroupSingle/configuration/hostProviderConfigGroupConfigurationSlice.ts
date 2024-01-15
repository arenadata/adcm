import { AdcmConfigShortView, AdcmConfiguration, ConfigurationAttributes, ConfigurationData } from '@models/adcm';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { AdcmHostProviderGroupConfigsConfigsApi, RequestError } from '@api';
import { showError } from '@store/notificationsSlice.ts';
import { getErrorMessage } from '@utils/httpResponseUtils.ts';
import { executeWithMinDelay } from '@utils/requestUtils.ts';
import { defaultSpinnerDelay } from '@constants';

type AdcmHostProviderConfigGroupConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
};

type LoadHostProviderConfigGroupConfigurationPayload = {
  hostProviderId: number;
  configGroupId: number;
  configId: number;
};

type SaveHostProviderConfigGroupConfigurationPayload = {
  hostProviderId: number;
  configGroupId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
};

const createHostProviderConfigGroupConfiguration = createAsyncThunk(
  'adcm/hostProvider/configGroup/configuration/createHostProviderConfigGroupConfiguration',
  async (
    {
      hostProviderId,
      configGroupId,
      configurationData,
      attributes,
      description,
    }: SaveHostProviderConfigGroupConfigurationPayload,
    thunkAPI,
  ) => {
    try {
      const configuration = await AdcmHostProviderGroupConfigsConfigsApi.createConfiguration(
        hostProviderId,
        configGroupId,
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

const createWithUpdateHostProviderConfigGroupConfigurations = createAsyncThunk(
  'adcm/hostProvider/configGroup/configuration/createAndUpdateHostProviderConfigGroupConfigurations',
  async (arg: SaveHostProviderConfigGroupConfigurationPayload, thunkAPI) => {
    await thunkAPI.dispatch(createHostProviderConfigGroupConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(
      getHostProviderConfigGroupConfigurationsVersions({
        hostProviderId: arg.hostProviderId,
        configGroupId: arg.configGroupId,
      }),
    );
  },
);

const getHostProviderConfigGroupConfiguration = createAsyncThunk(
  'adcm/hostProvider/configGroup/configuration/getHostProviderConfigGroupConfiguration',
  async (arg: LoadHostProviderConfigGroupConfigurationPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([
        AdcmHostProviderGroupConfigsConfigsApi.getConfig(arg),
        AdcmHostProviderGroupConfigsConfigsApi.getConfigSchema(arg),
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

type GetHostProviderConfigGroupConfigurationsPayload = {
  hostProviderId: number;
  configGroupId: number;
};

const getHostProviderConfigGroupConfigurationsVersions = createAsyncThunk(
  'adcm/hostProviders/configuration/getHostProviderConfigGroupConfigurationsVersions',
  async ({ hostProviderId, configGroupId }: GetHostProviderConfigGroupConfigurationsPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmHostProviderGroupConfigsConfigsApi.getConfigs(hostProviderId, configGroupId);
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

const createInitialState = (): AdcmHostProviderConfigGroupConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const hostProviderConfigGroupConfigurationSlice = createSlice({
  name: 'adcm/hostProvider/configGroup/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupHostProviderConfigGroupConfiguration() {
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
    builder.addCase(getHostProviderConfigGroupConfiguration.fulfilled, (state, action) => {
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
    builder.addCase(getHostProviderConfigGroupConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getHostProviderConfigGroupConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getHostProviderConfigGroupConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupHostProviderConfigGroupConfiguration, setIsConfigurationLoading, setIsVersionsLoading } =
  hostProviderConfigGroupConfigurationSlice.actions;
export {
  getHostProviderConfigGroupConfiguration,
  getHostProviderConfigGroupConfigurationsVersions,
  cleanupHostProviderConfigGroupConfiguration,
  createWithUpdateHostProviderConfigGroupConfigurations,
};
export default hostProviderConfigGroupConfigurationSlice.reducer;
