import { createSlice } from '@reduxjs/toolkit';
import { RequestError, AuthApi, AdcmProfileApi } from '@api';
// eslint-disable-next-line import/no-cycle
import { createAsyncThunk } from './redux';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { showError } from './notificationsSlice';
import { AdcmProfileUser } from '@models/adcm';

type LoginActionPayload = {
  username: string;
  password: string;
};

export enum AUTH_STATE {
  Checking = 'checking',
  NotAuth = 'not_auth',
  Authed = 'authed',
}
export type AuthState = AUTH_STATE.NotAuth | AUTH_STATE.Checking | AUTH_STATE.Authed;

type UserState = {
  username: string;
  needCheckSession: boolean;
  hasError: boolean;
  authState: AuthState;
  message: string;
  profile: AdcmProfileUser;
};

const login = createAsyncThunk('auth/login', async (arg: LoginActionPayload, thunkAPI) => {
  try {
    await AuthApi.login(arg.username, arg.password);
    return AdcmProfileApi.getProfile();
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const logout = createAsyncThunk('auth/logout', async (_, thunkAPI) => {
  try {
    return AuthApi.logout();
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const checkSession = createAsyncThunk('auth/checkSession', async (_, thunkAPI) => {
  try {
    return AdcmProfileApi.getProfile();
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): UserState => ({
  username: '',
  needCheckSession: true,
  hasError: false,
  authState: AUTH_STATE.NotAuth,
  message: '',
  profile: {} as AdcmProfileUser,
});

const authSlice = createSlice({
  name: 'auth',
  initialState: createInitialState(),
  reducers: {
    clearError(state) {
      state.hasError = false;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(login.pending, (state) => {
      state.message = '';
      state.hasError = false;
      state.needCheckSession = false;
      state.authState = AUTH_STATE.Checking;
    });
    builder.addCase(login.fulfilled, (state, action) => {
      state.username = action.payload.username;
      state.profile = action.payload;
      state.message = '';
      state.hasError = false;
      state.needCheckSession = false;
      state.authState = AUTH_STATE.Authed;
    });
    builder.addCase(login.rejected, (_, action) => {
      const error = action.payload as RequestError;
      return {
        ...createInitialState(),
        message: getErrorMessage(error),
        hasError: true,
        needCheckSession: false,
        authState: AUTH_STATE.NotAuth,
      };
    });

    builder.addCase(logout.fulfilled, () => {
      return {
        ...createInitialState(),
        hasError: false,
        needCheckSession: false,
        authState: AUTH_STATE.NotAuth,
      };
    });
    builder.addCase(logout.rejected, () => createInitialState());

    builder.addCase(checkSession.pending, (state) => {
      state.hasError = false;
      state.authState = AUTH_STATE.Checking;
    });
    builder.addCase(checkSession.fulfilled, (state, action) => {
      state.username = action.payload.username;
      state.profile = action.payload;
      state.hasError = false;
      state.needCheckSession = false;
      state.authState = AUTH_STATE.Authed;
    });
    builder.addCase(checkSession.rejected, (state) => {
      state.hasError = false;
      state.needCheckSession = false;
      state.authState = AUTH_STATE.NotAuth;
    });
  },
});

export const { clearError } = authSlice.actions;
export { login, logout, checkSession };
export default authSlice.reducer;
