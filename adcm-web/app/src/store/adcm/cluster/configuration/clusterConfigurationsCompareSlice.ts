import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmFullConfigurationInfo } from '@models/adcm/configuration';
import { AdcmClusterConfigsApi, RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

type AdcmClusterCompareConfigurationsState = {
  leftConfiguration: AdcmFullConfigurationInfo | null;
  rightConfiguration: AdcmFullConfigurationInfo | null;
  isLeftLoading: boolean;
  isRightLoading: boolean;
};

type LoadClusterConfigurationPayload = {
  clusterId: number;
  configId: number;
};

const loadClusterConfiguration = createAsyncThunk(
  'adcm/cluster/compareConfigurations/loadConfiguration',
  async (arg: LoadClusterConfigurationPayload, thunkAPI) => {
    try {
      const [config, schema] = await Promise.all([
        AdcmClusterConfigsApi.getConfig(arg.clusterId, arg.configId),
        AdcmClusterConfigsApi.getConfigSchema(arg.clusterId),
      ]);
      return { config, schema };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getLeftConfiguration = createAsyncThunk(
  'adcm/cluster/compareConfigurations/getLeftConfiguration',
  async (arg: LoadClusterConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadClusterConfiguration(arg)).unwrap();
  },
);

const getRightConfiguration = createAsyncThunk(
  'adcm/cluster/compareConfigurations/getRightConfiguration',
  async (arg: LoadClusterConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadClusterConfiguration(arg)).unwrap();
  },
);

const createInitialState = (): AdcmClusterCompareConfigurationsState => ({
  leftConfiguration: null,
  rightConfiguration: null,
  isLeftLoading: false,
  isRightLoading: false,
});

const clusterConfigurationsCompareSlice = createSlice({
  name: 'adcm/clusters/configurationsCompareSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterConfigurationsCompareSlice() {
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

const { cleanupClusterConfigurationsCompareSlice } = clusterConfigurationsCompareSlice.actions;
export { getRightConfiguration, getLeftConfiguration, cleanupClusterConfigurationsCompareSlice };
export default clusterConfigurationsCompareSlice.reducer;
