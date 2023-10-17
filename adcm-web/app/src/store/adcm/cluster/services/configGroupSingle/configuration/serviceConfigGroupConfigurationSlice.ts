import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServiceConfigGroupConfigsApi, RequestError } from '@api';
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

type AdcmServiceConfigGroupConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
};

type LoadServiceConfigGroupConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
  configId: number;
};

type SaveServiceConfigGroupConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
};

const createServiceConfigGroupConfiguration = createAsyncThunk(
  'adcm/service/configGroup/configuration/createServiceConfigGroupConfiguration',
  async (
    {
      clusterId,
      serviceId,
      configGroupId,
      configurationData,
      attributes,
      description,
    }: SaveServiceConfigGroupConfigurationPayload,
    thunkAPI,
  ) => {
    try {
      const configuration = await AdcmClusterServiceConfigGroupConfigsApi.createConfiguration(
        clusterId,
        serviceId,
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

const createWithUpdateServiceConfigGroupConfigurations = createAsyncThunk(
  'adcm/service/configGroup/configuration/createAndUpdateServiceConfigGroupConfigurations',
  async (arg: SaveServiceConfigGroupConfigurationPayload, thunkAPI) => {
    await thunkAPI.dispatch(createServiceConfigGroupConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(
      getServiceConfigGroupConfigurationsVersions({
        clusterId: arg.clusterId,
        serviceId: arg.serviceId,
        configGroupId: arg.configGroupId,
      }),
    );
  },
);

const getServiceConfigGroupConfiguration = createAsyncThunk(
  'adcm/service/configGroup/configuration/getServiceConfigGroupConfiguration',
  async ({ clusterId, serviceId, configGroupId, configId }: LoadServiceConfigGroupConfigurationPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([
        AdcmClusterServiceConfigGroupConfigsApi.getConfig(clusterId, serviceId, configGroupId, configId),
        AdcmClusterServiceConfigGroupConfigsApi.getConfigSchema(clusterId, serviceId, configGroupId),
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

type GetServiceConfigGroupConfigurationsPayload = {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
};

const getServiceConfigGroupConfigurationsVersions = createAsyncThunk(
  'adcm/clusters/configuration/getServiceConfigGroupConfigurationsVersions',
  async ({ clusterId, serviceId, configGroupId }: GetServiceConfigGroupConfigurationsPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmClusterServiceConfigGroupConfigsApi.getConfigs(clusterId, serviceId, configGroupId);
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

const createInitialState = (): AdcmServiceConfigGroupConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const serviceConfigGroupConfigurationSlice = createSlice({
  name: 'adcm/service/configGroup/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupServiceConfigGroupConfiguration() {
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
    builder.addCase(getServiceConfigGroupConfiguration.fulfilled, (state, action) => {
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
    builder.addCase(getServiceConfigGroupConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getServiceConfigGroupConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getServiceConfigGroupConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupServiceConfigGroupConfiguration, setIsConfigurationLoading, setIsVersionsLoading } =
  serviceConfigGroupConfigurationSlice.actions;
export {
  getServiceConfigGroupConfiguration,
  getServiceConfigGroupConfigurationsVersions,
  cleanupServiceConfigGroupConfiguration,
  createWithUpdateServiceConfigGroupConfigurations,
};
export default serviceConfigGroupConfigurationSlice.reducer;
