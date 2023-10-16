import { createSlice } from '@reduxjs/toolkit';
import { AdcmSettingsApi, RequestError } from '@api';
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

type AdcmSettingsState = {
  isConfigurationLoading: boolean;
  loadedConfiguration: AdcmConfiguration | null;
  configVersions: AdcmConfigShortView[];
  isVersionsLoading: boolean;
};

type SaveSettingsPayload = {
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
};

const createSettingsConfiguration = createAsyncThunk(
  'adcm/settings/configuration/createSettingsConfiguration',
  async ({ configurationData, attributes, description }: SaveSettingsPayload, thunkAPI) => {
    try {
      const configuration = await AdcmSettingsApi.createConfiguration(configurationData, attributes, description);
      return configuration;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createWithUpdateSettingsConfiguration = createAsyncThunk(
  'adcm/settings/configuration/createWithUpdateSettingsConfiguration',
  async (arg: SaveSettingsPayload, thunkAPI) => {
    await thunkAPI.dispatch(createSettingsConfiguration(arg)).unwrap();
    await thunkAPI.dispatch(getSettingsConfigurationVersions());
  },
);

const getSettingsConfiguration = createAsyncThunk(
  'adcm/settings/configuration/getSettings',
  async (id: number, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsConfigurationLoading(true));

    try {
      const [config, schema] = await Promise.all([AdcmSettingsApi.getConfig(id), AdcmSettingsApi.getConfigSchema()]);
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

const getSettingsConfigurationVersions = createAsyncThunk(
  'adcm/settings/configuration/getSettingsConfigurationVersions',
  async (arg, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsVersionsLoading(true));

    try {
      return await AdcmSettingsApi.getConfigs();
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

const createInitialState = (): AdcmSettingsState => ({
  isVersionsLoading: false,
  isConfigurationLoading: false,
  loadedConfiguration: null,
  configVersions: [],
});

const SettingsConfigurationsSlice = createSlice({
  name: 'adcm/settings/configuration',
  initialState: createInitialState(),
  reducers: {
    cleanupSettings() {
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
    builder.addCase(getSettingsConfiguration.fulfilled, (state, action) => {
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
    builder.addCase(getSettingsConfiguration.rejected, (state) => {
      state.loadedConfiguration = null;
    });
    builder.addCase(getSettingsConfigurationVersions.fulfilled, (state, action) => {
      state.configVersions = action.payload.results;
    });
    builder.addCase(getSettingsConfigurationVersions.rejected, (state) => {
      state.configVersions = [];
    });
  },
});

const { cleanupSettings, setIsConfigurationLoading, setIsVersionsLoading } = SettingsConfigurationsSlice.actions;
export {
  getSettingsConfiguration,
  getSettingsConfigurationVersions,
  cleanupSettings,
  createWithUpdateSettingsConfiguration,
};
export default SettingsConfigurationsSlice.reducer;
