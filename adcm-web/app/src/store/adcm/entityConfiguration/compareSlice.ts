import { AdcmFullConfigurationInfo } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { createSlice } from '@reduxjs/toolkit';
import { LoadEntityConfigurationArgs } from './entityConfiguration.types';
import { ApiRequests } from './entityConfiguration.constants';

type AdcmEntityCompareConfigurationsState = {
  leftConfiguration: AdcmFullConfigurationInfo | null;
  rightConfiguration: AdcmFullConfigurationInfo | null;
  isLeftLoading: boolean;
  isRightLoading: boolean;
};

const loadConfiguration = createAsyncThunk(
  'adcm/entityCompareConfigurations/loadConfiguration',
  async ({ entityType, args }: LoadEntityConfigurationArgs, thunkAPI) => {
    try {
      const requests = ApiRequests[entityType];
      const [config, schema] = await Promise.all([requests.getConfig(args), requests.getConfigSchema(args)]);
      return { config, schema };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getLeftConfiguration = createAsyncThunk(
  'adcm/entityCompareConfigurations/getLeftConfiguration',
  async (arg: LoadEntityConfigurationArgs, thunkAPI) => {
    return thunkAPI.dispatch(loadConfiguration(arg)).unwrap();
  },
);

const getRightConfiguration = createAsyncThunk(
  'adcm/entityCompareConfigurations/getRightConfiguration',
  async (arg: LoadEntityConfigurationArgs, thunkAPI) => {
    return thunkAPI.dispatch(loadConfiguration(arg)).unwrap();
  },
);

const createInitialState = (): AdcmEntityCompareConfigurationsState => ({
  leftConfiguration: null,
  rightConfiguration: null,
  isLeftLoading: false,
  isRightLoading: false,
});

const entityConfigurationsCompareSlice = createSlice({
  name: 'adcm/entityCompareConfigurations',
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

const { cleanupCompareSlice } = entityConfigurationsCompareSlice.actions;
export { getRightConfiguration, getLeftConfiguration, cleanupCompareSlice };
export default entityConfigurationsCompareSlice.reducer;
