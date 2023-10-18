import { AdcmFullConfigurationInfo } from '@models/adcm';
import { createAsyncThunk } from '@store/redux.ts';
import { AdcmHostProviderGroupConfigsConfigsApi, RequestError } from '@api';
import { showError } from '@store/notificationsSlice.ts';
import { getErrorMessage } from '@utils/httpResponseUtils.ts';
import { createSlice } from '@reduxjs/toolkit';

type AdcmHostProviderConfigGroupCompareConfigurationsState = {
  leftConfiguration: AdcmFullConfigurationInfo | null;
  rightConfiguration: AdcmFullConfigurationInfo | null;
  isLeftLoading: boolean;
  isRightLoading: boolean;
};

type LoadHostProviderGroupConfigConfigurationPayload = {
  hostProviderId: number;
  configGroupId: number;
  configId: number;
};

const loadHostProviderGroupConfigConfiguration = createAsyncThunk(
  'adcm/hostProvider/configGroup/compareConfigurations/loadConfiguration',
  async (arg: LoadHostProviderGroupConfigConfigurationPayload, thunkAPI) => {
    try {
      const [config, schema] = await Promise.all([
        AdcmHostProviderGroupConfigsConfigsApi.getConfig(arg.hostProviderId, arg.configGroupId, arg.configId),
        AdcmHostProviderGroupConfigsConfigsApi.getConfigSchema(arg.hostProviderId, arg.configGroupId),
      ]);
      return { config, schema };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getLeftConfiguration = createAsyncThunk(
  'adcm/hostProvider/configGroup/compareConfigurations/getLeftConfiguration',
  async (arg: LoadHostProviderGroupConfigConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadHostProviderGroupConfigConfiguration(arg)).unwrap();
  },
);

const getRightConfiguration = createAsyncThunk(
  'adcm/hostProvider/configGroup/compareConfigurations/getRightConfiguration',
  async (arg: LoadHostProviderGroupConfigConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadHostProviderGroupConfigConfiguration(arg)).unwrap();
  },
);

const createInitialState = (): AdcmHostProviderConfigGroupCompareConfigurationsState => ({
  leftConfiguration: null,
  rightConfiguration: null,
  isLeftLoading: false,
  isRightLoading: false,
});

const hostProviderConfigGroupConfigurationsCompareSlice = createSlice({
  name: 'adcm/hostProviders/configGroup/configurationsCompareSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupCompareSlice() {
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

const { cleanupCompareSlice } = hostProviderConfigGroupConfigurationsCompareSlice.actions;
export { getRightConfiguration, getLeftConfiguration, cleanupCompareSlice };
export default hostProviderConfigGroupConfigurationsCompareSlice.reducer;
