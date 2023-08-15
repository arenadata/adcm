import { createSlice } from '@reduxjs/toolkit';
import { RequestError, UserApi } from '@api';
import { createAsyncThunk } from './redux';
import { getErrorMessage } from '@utils/httpResponseUtils';

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
};

const login = createAsyncThunk('user/login', async (arg: LoginActionPayload, thunkAPI) => {
  try {
    await UserApi.login(arg.username, arg.password);
    return UserApi.getCurrentUser();
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const logout = createAsyncThunk('user/logout', async (_, thunkAPI) => {
  try {
    return UserApi.logout();
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const checkSession = createAsyncThunk('user/checkSession', async (_, thunkAPI) => {
  try {
    return UserApi.getCurrentUser();
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
});

const userSlice = createSlice({
  name: 'user',
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

export const { clearError } = userSlice.actions;
export { login, logout, checkSession };
export default userSlice.reducer;
