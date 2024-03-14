import { RequestError } from '@api';
import { AdcmProfileApi } from '@api/adcm/profile';
import { AdcmProfileChangePassword, AdcmProfileUser } from '@models/adcm/profile';
import { createSlice } from '@reduxjs/toolkit';
import { showError, showSuccess } from '@store/notificationsSlice';
import { createAsyncThunk } from '@store/redux';
import { logout } from '@store/authSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

interface AdcmProfileState {
  profile: AdcmProfileUser;
}

const getProfile = createAsyncThunk('adcm/profile', async (arg, thunkAPI) => {
  try {
    return await AdcmProfileApi.getProfile();
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
});

const profileSlice = createSlice({
  name: 'adcm/profile',
  initialState: createInitialState(),
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(getProfile.fulfilled, (state, action) => {
      state.profile = action.payload;
    });
  },
});

export { getProfile, changePassword };
export default profileSlice.reducer;
