import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServiceComponentsConfigsApi, RequestError } from '@api';
import { getErrorMessage } from '@utils/httpResponseUtils.ts';
import { showError } from '@store/notificationsSlice.ts';
import { AdcmFullConfigurationInfo } from '@models/adcm';

type AdcmServiceComponentCompareConfigurationsState = {
  leftConfiguration: AdcmFullConfigurationInfo | null;
  rightConfiguration: AdcmFullConfigurationInfo | null;
  isLeftLoading: boolean;
  isRightLoading: boolean;
};

type LoadServiceComponentConfigurationPayload = {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configId: number;
};

const loadServiceComponentConfiguration = createAsyncThunk(
  'adcm/component/compareConfigurations/loadConfiguration',
  async (arg: LoadServiceComponentConfigurationPayload, thunkAPI) => {
    try {
      const [config, schema] = await Promise.all([
        AdcmClusterServiceComponentsConfigsApi.getConfig(arg.clusterId, arg.serviceId, arg.componentId, arg.configId),
        AdcmClusterServiceComponentsConfigsApi.getConfigSchema(arg.clusterId, arg.serviceId, arg.componentId),
      ]);
      return { config, schema };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getLeftConfiguration = createAsyncThunk(
  'adcm/component/compareConfigurations/getLeftConfiguration',
  async (arg: LoadServiceComponentConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadServiceComponentConfiguration(arg)).unwrap();
  },
);

const getRightConfiguration = createAsyncThunk(
  'adcm/component/compareConfigurations/getRightConfiguration',
  async (arg: LoadServiceComponentConfigurationPayload, thunkAPI) => {
    return thunkAPI.dispatch(loadServiceComponentConfiguration(arg)).unwrap();
  },
);

const createInitialState = (): AdcmServiceComponentCompareConfigurationsState => ({
  leftConfiguration: null,
  rightConfiguration: null,
  isLeftLoading: false,
  isRightLoading: false,
});

const serviceComponentConfigurationsCompareSlice = createSlice({
  name: 'adcm/component/configurationsCompareSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupServiceComponentConfigurationsCompareSlice() {
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

const { cleanupServiceComponentConfigurationsCompareSlice } = serviceComponentConfigurationsCompareSlice.actions;
export { getRightConfiguration, getLeftConfiguration, cleanupServiceComponentConfigurationsCompareSlice };
export default serviceComponentConfigurationsCompareSlice.reducer;
