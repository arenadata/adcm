import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterGroupConfigsConfigsApi, RequestError } from '@api';
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

type AdcmClusterConfigGroupConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
};

type LoadClusterConfigGroupConfigurationPayload = {
  clusterId: number;
  configGroupId: number;
  configId: number;
};

type SaveClusterConfigGroupConfigurationPayload = {
  clusterId: number;
  configGroupId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
};

const createClusterConfigGroupConfiguration = createAsyncThunk(
  'adcm/cluster/configGroup/configuration/createClusterConfigGroupConfiguration',
  async (
    {
      clusterId,
      configGroupId,
      configurationData,
      attributes,
      description,
    }: SaveClusterConfigGroupConfigurationPayload,
    thunkAPI,
  ) => {
    try {
      const configuration = await AdcmClusterGroupConfigsConfigsApi.createConfiguration(
        clusterId,
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

const createWithUpdateClusterConfigGroupConfigurations = createAsyncThunk(
  'adcm/cluster/configGroup/configuration/createAndUpdateClusterConfigGroupConfigurations',
  async (arg: SaveClusterConfigGroupConfigurationPayload, thunkAPI) => {
    await thunkAPI.dispatch(createClusterConfigGroupConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(
      getClusterConfigGroupConfigurationsVersions({ clusterId: arg.clusterId, configGroupId: arg.configGroupId }),
    );
  },
);

const getClusterConfigGroupConfiguration = createAsyncThunk(
  'adcm/cluster/configGroup/configuration/getClusterConfigGroupConfiguration',
  async (arg: LoadClusterConfigGroupConfigurationPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([
        AdcmClusterGroupConfigsConfigsApi.getConfig(arg.clusterId, arg.configGroupId, arg.configId),
        AdcmClusterGroupConfigsConfigsApi.getConfigSchema(arg.clusterId, arg.configGroupId),
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

type GetClusterConfigGroupConfigurationsPayload = {
  clusterId: number;
  configGroupId: number;
};

const getClusterConfigGroupConfigurationsVersions = createAsyncThunk(
  'adcm/clusters/configuration/getClusterConfigGroupConfigurationsVersions',
  async ({ clusterId, configGroupId }: GetClusterConfigGroupConfigurationsPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmClusterGroupConfigsConfigsApi.getConfigs(clusterId, configGroupId);
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

const createInitialState = (): AdcmClusterConfigGroupConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const clusterConfigGroupConfigurationSlice = createSlice({
  name: 'adcm/cluster/configGroup/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterConfigGroupConfiguration() {
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
    builder.addCase(getClusterConfigGroupConfiguration.fulfilled, (state, action) => {
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
    builder.addCase(getClusterConfigGroupConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getClusterConfigGroupConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getClusterConfigGroupConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupClusterConfigGroupConfiguration, setIsConfigurationLoading, setIsVersionsLoading } =
  clusterConfigGroupConfigurationSlice.actions;
export {
  getClusterConfigGroupConfiguration,
  getClusterConfigGroupConfigurationsVersions,
  cleanupClusterConfigGroupConfiguration,
  createWithUpdateClusterConfigGroupConfigurations,
};
export default clusterConfigGroupConfigurationSlice.reducer;
