import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterConfigsApi, RequestError } from '@api';
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

type AdcmClusterConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
};

type LoadClusterConfigurationPayload = {
  clusterId: number;
  configId: number;
};

type SaveClusterConfigurationPayload = {
  clusterId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
};

const createClusterConfiguration = createAsyncThunk(
  'adcm/cluster/configuration/createClusterConfiguration',
  async ({ clusterId, configurationData, attributes, description }: SaveClusterConfigurationPayload, thunkAPI) => {
    try {
      const configuration = await AdcmClusterConfigsApi.createConfiguration(
        clusterId,
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

const createWithUpdateClusterConfigurations = createAsyncThunk(
  'adcm/cluster/configuration/createAndUpdateClusterConfigurations',
  async (arg: SaveClusterConfigurationPayload, thunkAPI) => {
    await thunkAPI.dispatch(createClusterConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(getClusterConfigurationsVersions({ clusterId: arg.clusterId }));
  },
);

const getClusterConfiguration = createAsyncThunk(
  'adcm/cluster/configuration/getClusterConfiguration',
  async (arg: LoadClusterConfigurationPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([
        AdcmClusterConfigsApi.getConfig(arg),
        AdcmClusterConfigsApi.getConfigSchema(arg),
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

type GetClusterConfigurationsPayload = {
  clusterId: number;
};

const getClusterConfigurationsVersions = createAsyncThunk(
  'adcm/clusters/configuration/getClusterConfigurationsVersions',
  async ({ clusterId }: GetClusterConfigurationsPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmClusterConfigsApi.getConfigs(clusterId);
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

const createInitialState = (): AdcmClusterConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const clusterConfigurationSlice = createSlice({
  name: 'adcm/cluster/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterConfiguration() {
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
    builder.addCase(getClusterConfiguration.fulfilled, (state, action) => {
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
    builder.addCase(getClusterConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getClusterConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getClusterConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupClusterConfiguration, setIsConfigurationLoading, setIsVersionsLoading } =
  clusterConfigurationSlice.actions;
export {
  getClusterConfiguration,
  getClusterConfigurationsVersions,
  cleanupClusterConfiguration,
  createWithUpdateClusterConfigurations,
};
export default clusterConfigurationSlice.reducer;
