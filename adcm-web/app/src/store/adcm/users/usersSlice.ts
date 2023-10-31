import { createSlice } from '@reduxjs/toolkit';
import { AdcmUsersApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmUser } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';

interface AdcmUsersState {
  users: AdcmUser[];
  totalCount: number;
  isLoading: boolean;
}

const loadFromBackend = createAsyncThunk('adcm/users/loadFromBackend', async (arg, thunkAPI) => {
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

const getUsers = createAsyncThunk('adcm/users/getUsers', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadFromBackend());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshUsers = createAsyncThunk('adcm/users/refreshUsers', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadFromBackend());
});

const createInitialState = (): AdcmUsersState => ({
  users: [],
  totalCount: 0,
  isLoading: false,
});

const usersSlice = createSlice({
  name: 'adcm/users',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
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

const { setIsLoading, cleanupUsers } = usersSlice.actions;
export { getUsers, refreshUsers, cleanupUsers };
export default usersSlice.reducer;
