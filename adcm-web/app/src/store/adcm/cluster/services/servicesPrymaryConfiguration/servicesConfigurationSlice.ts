import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServicesConfigsApi, RequestError } from '@api';
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

type AdcmClusterServicesConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
};

type LoadClusterServicesConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  configId: number;
};

type SaveClusterServicesConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
};

const createClusterServiceConfiguration = createAsyncThunk(
  'adcm/clusterServices/configuration/createClusterServiceConfiguration',
  async (
    { clusterId, serviceId, configurationData, attributes, description }: SaveClusterServicesConfigurationPayload,
    thunkAPI,
  ) => {
    try {
      const configuration = await AdcmClusterServicesConfigsApi.createConfiguration(
        clusterId,
        serviceId,
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

const createWithUpdateClusterServicesConfigurations = createAsyncThunk(
  'adcm/clusterServices/configuration/createWithUpdateClusterServicesConfigurations',
  async (arg: SaveClusterServicesConfigurationPayload, thunkAPI) => {
    await thunkAPI.dispatch(createClusterServiceConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(
      getClusterServicesConfigurationsVersions({ clusterId: arg.clusterId, serviceId: arg.serviceId }),
    );
  },
);

const getClusterServicesConfiguration = createAsyncThunk(
  'adcm/clusterServices/configuration/getClusterServicesConfiguration',
  async (arg: LoadClusterServicesConfigurationPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([
        AdcmClusterServicesConfigsApi.getConfig(arg.clusterId, arg.serviceId, arg.configId),
        AdcmClusterServicesConfigsApi.getConfigSchema(arg.clusterId, arg.serviceId),
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

type GetClusterServicesConfigurationsPayload = {
  clusterId: number;
  serviceId: number;
};

const getClusterServicesConfigurationsVersions = createAsyncThunk(
  'adcm/clusterServices/configuration/getClusterServicesConfigurationsVersions',
  async ({ clusterId, serviceId }: GetClusterServicesConfigurationsPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmClusterServicesConfigsApi.getConfigs(clusterId, serviceId);
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

const createInitialState = (): AdcmClusterServicesConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const clusterServicesConfigurationSlice = createSlice({
  name: 'adcm/clusterServices/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterServicesConfiguration() {
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
    builder.addCase(getClusterServicesConfiguration.fulfilled, (state, action) => {
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
    builder.addCase(getClusterServicesConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getClusterServicesConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getClusterServicesConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupClusterServicesConfiguration, setIsConfigurationLoading, setIsVersionsLoading } =
  clusterServicesConfigurationSlice.actions;
export {
  getClusterServicesConfiguration,
  getClusterServicesConfigurationsVersions,
  cleanupClusterServicesConfiguration,
  createWithUpdateClusterServicesConfigurations,
};
export default clusterServicesConfigurationSlice.reducer;
