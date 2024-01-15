import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServiceComponentGroupConfigConfigsApi, RequestError } from '@api';
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

type AdcmServiceComponentConfigGroupConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
};

type LoadServiceComponentConfigGroupConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configGroupId: number;
  configId: number;
};

type SaveServiceComponentConfigGroupConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configGroupId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
};

const createServiceComponentConfigGroupConfiguration = createAsyncThunk(
  'adcm/serviceComponent/configGroup/configuration/createServiceComponentConfigGroupConfiguration',
  async (
    {
      clusterId,
      serviceId,
      componentId,
      configGroupId,
      configurationData,
      attributes,
      description,
    }: SaveServiceComponentConfigGroupConfigurationPayload,
    thunkAPI,
  ) => {
    try {
      const configuration = await AdcmClusterServiceComponentGroupConfigConfigsApi.createConfiguration(
        clusterId,
        serviceId,
        componentId,
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

const createWithUpdateServiceComponentConfigGroupConfigurations = createAsyncThunk(
  'adcm/cluster/configGroup/configuration/createAndUpdateServiceComponentConfigGroupConfigurations',
  async (arg: SaveServiceComponentConfigGroupConfigurationPayload, thunkAPI) => {
    await thunkAPI.dispatch(createServiceComponentConfigGroupConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(
      getServiceComponentConfigGroupConfigurationsVersions({
        clusterId: arg.clusterId,
        serviceId: arg.serviceId,
        componentId: arg.componentId,
        configGroupId: arg.configGroupId,
      }),
    );
  },
);

const getServiceComponentConfigGroupConfiguration = createAsyncThunk(
  'adcm/serviceComponent/configGroup/configuration/getServiceComponentConfigGroupConfiguration',
  async (args: LoadServiceComponentConfigGroupConfigurationPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([
        AdcmClusterServiceComponentGroupConfigConfigsApi.getConfig(args),
        AdcmClusterServiceComponentGroupConfigConfigsApi.getConfigSchema(args),
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

type GetServiceComponentConfigGroupConfigurationsPayload = {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configGroupId: number;
};

const getServiceComponentConfigGroupConfigurationsVersions = createAsyncThunk(
  'adcm/serviceComponent/configuration/getServiceComponentConfigGroupConfigurationsVersions',
  async (
    { clusterId, serviceId, componentId, configGroupId }: GetServiceComponentConfigGroupConfigurationsPayload,
    thunkAPI,
  ) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmClusterServiceComponentGroupConfigConfigsApi.getConfigs(
        clusterId,
        serviceId,
        componentId,
        configGroupId,
      );
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

const createInitialState = (): AdcmServiceComponentConfigGroupConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const serviceComponentConfigGroupConfigurationSlice = createSlice({
  name: 'adcm/serviceComponent/configGroup/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupServiceComponentConfigGroupConfiguration() {
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
    builder.addCase(getServiceComponentConfigGroupConfiguration.fulfilled, (state, action) => {
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
    builder.addCase(getServiceComponentConfigGroupConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getServiceComponentConfigGroupConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getServiceComponentConfigGroupConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupServiceComponentConfigGroupConfiguration, setIsConfigurationLoading, setIsVersionsLoading } =
  serviceComponentConfigGroupConfigurationSlice.actions;
export {
  getServiceComponentConfigGroupConfiguration,
  getServiceComponentConfigGroupConfigurationsVersions,
  cleanupServiceComponentConfigGroupConfiguration,
  createWithUpdateServiceComponentConfigGroupConfigurations,
};
export default serviceComponentConfigGroupConfigurationSlice.reducer;
