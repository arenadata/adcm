import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServiceComponentsConfigsApi, RequestError } from '@api';
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

type AdcmServiceComponentConfigurationState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
};

type LoadServiceComponentConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configId: number;
};

type SaveServiceComponentConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  componentId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
};

const createServiceComponentConfiguration = createAsyncThunk(
  'adcm/component/configuration/createServiceComponentConfiguration',
  async (
    {
      clusterId,
      serviceId,
      componentId,
      configurationData,
      attributes,
      description,
    }: SaveServiceComponentConfigurationPayload,
    thunkAPI,
  ) => {
    try {
      const configuration = await AdcmClusterServiceComponentsConfigsApi.createConfiguration(
        clusterId,
        serviceId,
        componentId,
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

const createWithUpdateServiceComponentConfigurations = createAsyncThunk(
  'adcm/component/configuration/createAndUpdateServiceComponentConfigurations',
  async (arg: SaveServiceComponentConfigurationPayload, thunkAPI) => {
    await thunkAPI.dispatch(createServiceComponentConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(
      getServiceComponentConfigurationsVersions({
        clusterId: arg.clusterId,
        serviceId: arg.serviceId,
        componentId: arg.componentId,
      }),
    );
  },
);

const getServiceComponentConfiguration = createAsyncThunk(
  'adcm/component/configuration/getServiceComponentConfiguration',
  async (arg: LoadServiceComponentConfigurationPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([
        AdcmClusterServiceComponentsConfigsApi.getConfig(arg),
        AdcmClusterServiceComponentsConfigsApi.getConfigSchema(arg),
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

type GetServiceComponentConfigurationsPayload = {
  clusterId: number;
  serviceId: number;
  componentId: number;
};

const getServiceComponentConfigurationsVersions = createAsyncThunk(
  'adcm/component/configuration/getServiceComponentConfigurationsVersions',
  async ({ clusterId, serviceId, componentId }: GetServiceComponentConfigurationsPayload, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmClusterServiceComponentsConfigsApi.getConfigs(clusterId, serviceId, componentId);
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

const createInitialState = (): AdcmServiceComponentConfigurationState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const serviceComponentConfigurationSlice = createSlice({
  name: 'adcm/component/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupServiceComponentConfiguration() {
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
    builder.addCase(getServiceComponentConfiguration.fulfilled, (state, action) => {
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
    builder.addCase(getServiceComponentConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getServiceComponentConfigurationsVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getServiceComponentConfigurationsVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupServiceComponentConfiguration, setIsConfigurationLoading, setIsVersionsLoading } =
  serviceComponentConfigurationSlice.actions;
export {
  getServiceComponentConfiguration,
  getServiceComponentConfigurationsVersions,
  cleanupServiceComponentConfiguration,
  createWithUpdateServiceComponentConfigurations,
};
export default serviceComponentConfigurationSlice.reducer;
