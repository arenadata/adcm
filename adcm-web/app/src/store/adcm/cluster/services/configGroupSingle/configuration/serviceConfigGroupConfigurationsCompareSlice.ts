import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmFullConfigurationInfo } from '@models/adcm/configuration';
import { AdcmClusterServiceConfigGroupConfigsApi, RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

type AdcmServiceConfigGroupCompareConfigurationsState = {
  leftConfiguration: AdcmFullConfigurationInfo | null;
  rightConfiguration: AdcmFullConfigurationInfo | null;
  isLeftLoading: boolean;
  isRightLoading: boolean;
};

type LoadServiceGroupConfigConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
  configId: number;
};

const loadServiceGroupConfigConfiguration = createAsyncThunk(
  'adcm/service/configGroup/compareConfigurations/loadConfiguration',
  async ({ clusterId, serviceId, configGroupId, configId }: LoadServiceGroupConfigConfigurationPayload, thunkAPI) => {
    try {
      const [config, schema] = await Promise.all([
        AdcmClusterServiceConfigGroupConfigsApi.getConfig(clusterId, serviceId, configGroupId, configId),
        AdcmClusterServiceConfigGroupConfigsApi.getConfigSchema(clusterId, serviceId, configGroupId),
      ]);
      return { config, schema };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getLeftConfiguration = createAsyncThunk(
  'adcm/service/configGroup/compareConfigurations/getLeftConfiguration',
  async (arg: LoadServiceGroupConfigConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadServiceGroupConfigConfiguration(arg)).unwrap();
  },
);

const getRightConfiguration = createAsyncThunk(
  'adcm/service/configGroup/compareConfigurations/getRightConfiguration',
  async (arg: LoadServiceGroupConfigConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadServiceGroupConfigConfiguration(arg)).unwrap();
  },
);

const createInitialState = (): AdcmServiceConfigGroupCompareConfigurationsState => ({
  leftConfiguration: null,
  rightConfiguration: null,
  isLeftLoading: false,
  isRightLoading: false,
});

const serviceConfigGroupConfigurationsCompareSlice = createSlice({
  name: 'adcm/service/configGroup/configurationsCompareSlice',
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

const { cleanupCompareSlice } = serviceConfigGroupConfigurationsCompareSlice.actions;
export { getRightConfiguration, getLeftConfiguration, cleanupCompareSlice };
export default serviceConfigGroupConfigurationsCompareSlice.reducer;
