import { AdcmSettingsApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmSettings } from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

interface AdcmSettingsState {
  adcmSettings: AdcmSettings | null;
}

const getAdcmSettings = createAsyncThunk('adcm/adcmSettings/getAdcmSettings', async (arg: void, thunkAPI) => {
  try {
    const adcmSettings = await AdcmSettingsApi.getSettings();
    return adcmSettings;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): AdcmSettingsState => ({
  adcmSettings: null,
});

const adcmSettingsSlice = createSlice({
  name: 'adcm/adcmSettings',
  initialState: createInitialState(),
  reducers: {
    cleanupAdcmSettings() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getAdcmSettings.fulfilled, (state, action) => {
      state.adcmSettings = action.payload;
    });
    builder.addCase(getAdcmSettings.rejected, (state) => {
      state.adcmSettings = null;
    });
  },
});

const { cleanupAdcmSettings } = adcmSettingsSlice.actions;
export { cleanupAdcmSettings, getAdcmSettings };

export default adcmSettingsSlice.reducer;
