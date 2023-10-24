import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmFullConfigurationInfo } from '@models/adcm/configuration';
import { AdcmHostProviderConfigsApi, RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

type AdcmHostProviderCompareConfigurationsState = {
  leftConfiguration: AdcmFullConfigurationInfo | null;
  rightConfiguration: AdcmFullConfigurationInfo | null;
  isLeftLoading: boolean;
  isRightLoading: boolean;
};

type LoadHostProviderConfigurationPayload = {
  hostProviderId: number;
  configId: number;
};

const loadHostProviderConfiguration = createAsyncThunk(
  'adcm/hostProvider/compareConfigurations/loadConfiguration',
  async (arg: LoadHostProviderConfigurationPayload, thunkAPI) => {
    try {
      const [config, schema] = await Promise.all([
        AdcmHostProviderConfigsApi.getConfig(arg.hostProviderId, arg.configId),
        AdcmHostProviderConfigsApi.getConfigSchema(arg.hostProviderId),
      ]);
      return { config, schema };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getLeftConfiguration = createAsyncThunk(
  'adcm/hostProvider/compareConfigurations/getLeftConfiguration',
  async (arg: LoadHostProviderConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadHostProviderConfiguration(arg)).unwrap();
  },
);

const getRightConfiguration = createAsyncThunk(
  'adcm/hostProvider/compareConfigurations/getRightConfiguration',
  async (arg: LoadHostProviderConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadHostProviderConfiguration(arg)).unwrap();
  },
);

const createInitialState = (): AdcmHostProviderCompareConfigurationsState => ({
  leftConfiguration: null,
  rightConfiguration: null,
  isLeftLoading: false,
  isRightLoading: false,
});

const hostProviderConfigurationsCompareSlice = createSlice({
  name: 'adcm/hostProvider/configurationsCompareSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupHostProviderConfigurationsCompareSlice() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getLeftConfiguration.pending, (state) => {
      state.isLeftLoading = true;
    });
    builder.addCase(getLeftConfiguration.fulfilled, (state, action) => {
      const {
        config: { config: configurationData, adcmMeta: attributes, id, creationTime, description, isCurrent },
        schema,
      } = action.payload;
      // https://github.com/microsoft/TypeScript/issues/34933
      // cast to any to avoid compiler warning
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      state.leftConfiguration = {
        id,
        creationTime,
        description,
        isCurrent,
        configuration: {
          configurationData,
          attributes,
          schema,
        },
      };

      state.isLeftLoading = false;
    });
    builder.addCase(getLeftConfiguration.rejected, (state) => {
      state.leftConfiguration = null;
      state.isLeftLoading = false;
    });
    builder.addCase(getRightConfiguration.pending, (state) => {
      state.isLeftLoading = true;
    });
    builder.addCase(getRightConfiguration.fulfilled, (state, action) => {
      const {
        config: { config: configurationData, adcmMeta: attributes, id, creationTime, description, isCurrent },
        schema,
      } = action.payload;
      // https://github.com/microsoft/TypeScript/issues/34933
      // cast to any to avoid compiler warning
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      state.rightConfiguration = {
        id,
        creationTime,
        description,
        isCurrent,
        configuration: {
          configurationData,
          attributes,
          schema,
        },
      };

      state.isRightLoading = false;
    });
    builder.addCase(getRightConfiguration.rejected, (state) => {
      state.rightConfiguration = null;
      state.isRightLoading = false;
    });
  },
});

const { cleanupHostProviderConfigurationsCompareSlice } = hostProviderConfigurationsCompareSlice.actions;
export { getRightConfiguration, getLeftConfiguration, cleanupHostProviderConfigurationsCompareSlice };
export default hostProviderConfigurationsCompareSlice.reducer;
