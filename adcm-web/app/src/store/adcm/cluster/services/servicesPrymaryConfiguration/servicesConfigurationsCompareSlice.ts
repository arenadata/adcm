import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmFullConfigurationInfo } from '@models/adcm/configuration';
import { AdcmClusterServicesConfigsApi, RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

type AdcmClusterServicesCompareConfigurationsState = {
  leftConfiguration: AdcmFullConfigurationInfo | null;
  rightConfiguration: AdcmFullConfigurationInfo | null;
  isLeftLoading: boolean;
  isRightLoading: boolean;
};

type LoadClusterServicesConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  configId: number;
};

const loadClusterServicesConfiguration = createAsyncThunk(
  'adcm/clusterServices/compareConfigurations/loadConfiguration',
  async (arg: LoadClusterServicesConfigurationPayload, thunkAPI) => {
    try {
      const [config, schema] = await Promise.all([
        AdcmClusterServicesConfigsApi.getConfig(arg.clusterId, arg.serviceId, arg.configId),
        AdcmClusterServicesConfigsApi.getConfigSchema(arg.clusterId, arg.serviceId),
      ]);
      return { config, schema };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getLeftConfiguration = createAsyncThunk(
  'adcm/clusterServices/compareConfigurations/getLeftConfiguration',
  async (arg: LoadClusterServicesConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadClusterServicesConfiguration(arg)).unwrap();
  },
);

const getRightConfiguration = createAsyncThunk(
  'adcm/clusterServices/compareConfigurations/getRightConfiguration',
  async (arg: LoadClusterServicesConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadClusterServicesConfiguration(arg)).unwrap();
  },
);

const createInitialState = (): AdcmClusterServicesCompareConfigurationsState => ({
  leftConfiguration: null,
  rightConfiguration: null,
  isLeftLoading: false,
  isRightLoading: false,
});

const clusterServicesConfigurationsCompareSlice = createSlice({
  name: 'adcm/clusterServices/configurationsCompareSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterServicesConfigurationsCompareSlice() {
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

const { cleanupClusterServicesConfigurationsCompareSlice } = clusterServicesConfigurationsCompareSlice.actions;
export { getRightConfiguration, getLeftConfiguration, cleanupClusterServicesConfigurationsCompareSlice };
export default clusterServicesConfigurationsCompareSlice.reducer;
