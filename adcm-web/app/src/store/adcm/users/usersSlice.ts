import { createSlice } from '@reduxjs/toolkit';
import { AdcmUsersApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import type { AdcmUser } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { LoadState } from '@models/loadState';

interface AdcmUsersState {
  users: AdcmUser[];
  totalCount: number;
  loadState: LoadState;
}

const loadFromBackend = createAsyncThunk('adcm/users/loadFromBackend', async (_arg, thunkAPI) => {
  const {
    adcm: {
      usersTable: { filter, paginationParams, sortParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmUsersApi.getUsers(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getUsers = createAsyncThunk('adcm/users/getUsers', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(setLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadFromBackend());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLoadState(LoadState.Loaded));
    },
  });
});

const refreshUsers = createAsyncThunk('adcm/users/refreshUsers', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(loadFromBackend());
});

const createInitialState = (): AdcmUsersState => ({
  users: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
});

const usersSlice = createSlice({
  name: 'adcm/users',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
    cleanupUsers() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadFromBackend.fulfilled, (state, action) => {
        state.users = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(loadFromBackend.rejected, (state) => {
        state.users = [];
      });
  },
});

const { setLoadState, cleanupUsers } = usersSlice.actions;
export { getUsers, refreshUsers, cleanupUsers, setLoadState };
export default usersSlice.reducer;
