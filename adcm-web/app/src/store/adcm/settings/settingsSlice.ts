import type { RequestError } from '@api';
import { AdcmSettingsApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import type { AdcmSettings } from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';

interface AdcmSettingsState {
  adcmSettings: AdcmSettings | null;
}

const getAdcmSettings = createAsyncThunk('adcm/adcmSettings/getAdcmSettings', async (_, thunkAPI) => {
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
    builder.addCase(wsActions.create_adcm_concern, (state, action) => {
      const { id: adcmId, changes: newConcern } = action.payload.object;
      if (
        state.adcmSettings?.id === adcmId &&
        state.adcmSettings.concerns.every((concern) => concern.id !== newConcern.id)
      ) {
        state.adcmSettings = {
          ...state.adcmSettings,
          concerns: [...state.adcmSettings.concerns, newConcern],
        };
      }
    });
    builder.addCase(wsActions.delete_adcm_concern, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.adcmSettings?.id === id) {
        state.adcmSettings = {
          ...state.adcmSettings,
          concerns: state.adcmSettings.concerns.filter((concern) => concern.id !== changes.id),
        };
      }
    });
  },
});

const { cleanupAdcmSettings } = adcmSettingsSlice.actions;
export { cleanupAdcmSettings, getAdcmSettings };

export default adcmSettingsSlice.reducer;
