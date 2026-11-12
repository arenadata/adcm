import type { RequestError } from '@api';
import { AdcmProfileApi } from '@api/adcm/profile';
import type { AdcmProfileChangePassword, AdcmProfileUser } from '@models/adcm/profile';
import { createSlice } from '@reduxjs/toolkit';
import { showError, showSuccess } from '@store/notificationsSlice';
import { createAsyncThunk } from '@store/redux';
import { logout, setProfile } from '@store/authSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

interface AdcmProfileState {
  profile: AdcmProfileUser;
  isProfileLoading: boolean;
}

const getProfile = createAsyncThunk('adcm/profile', async (_arg, thunkAPI) => {
  try {
    const profile = await AdcmProfileApi.getProfile();
    thunkAPI.dispatch(setProfile(profile));
    return profile;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const changePassword = createAsyncThunk(
  'adcm/profile/password',
  async (payload: AdcmProfileChangePassword, thunkAPI) => {
    try {
      await AdcmProfileApi.changePassword(payload);
      await thunkAPI.dispatch(logout());
      thunkAPI.dispatch(showSuccess({ message: 'Password successfully changed' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

const createInitialState = (): AdcmProfileState => ({
  profile: {} as AdcmProfileUser,
  isProfileLoading: true,
});

const profileSlice = createSlice({
  name: 'adcm/profile',
  initialState: createInitialState(),
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(getProfile.pending, (state) => {
      state.isProfileLoading = true;
    });
    builder.addCase(getProfile.fulfilled, (state, action) => {
      state.profile = action.payload;
      state.isProfileLoading = false;
    });
    builder.addCase(getProfile.rejected, (state) => {
      state.isProfileLoading = false;
    });
  },
});

export { getProfile, changePassword };
export default profileSlice.reducer;
