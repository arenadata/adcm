import { createSlice } from '@reduxjs/toolkit';
import { AdcmUsersApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmUser } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

interface AdcmUsersState {
  users: AdcmUser[];
  totalCount: number;
  itemsForActions: {
    deletableId: number | null;
  };
  isLoading: boolean;
  selectedItemsIds: number[];
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

  thunkAPI.dispatch(loadFromBackend());
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

const deleteUserWithUpdate = createAsyncThunk('adcm/users/removeUser', async (id: number, thunkAPI) => {
  try {
    await AdcmUsersApi.deleteUser(id);
    await thunkAPI.dispatch(refreshUsers());
    thunkAPI.dispatch(showInfo({ message: 'User has been removed' }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const deleteUsersWithUpdate = createAsyncThunk('adcm/users/removeUsers', async (ids: number[], thunkAPI) => {
  try {
    await AdcmUsersApi.deleteUsers(ids);
    thunkAPI.dispatch(showInfo({ message: 'Users have been removed' }));
    await thunkAPI.dispatch(getUsers());
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const createInitialState = (): AdcmUsersState => ({
  users: [],
  totalCount: 0,
  itemsForActions: {
    deletableId: null,
  },
  isLoading: false,
  selectedItemsIds: [],
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
    cleanupItemsForActions(state) {
      state.itemsForActions = createInitialState().itemsForActions;
    },
    setDeletableId(state, action) {
      state.itemsForActions.deletableId = action.payload;
    },
    setSelectedItemsIds(state, action) {
      state.selectedItemsIds = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadFromBackend.fulfilled, (state, action) => {
      state.users = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadFromBackend.rejected, (state) => {
      state.users = [];
    });
    builder.addCase(deleteUserWithUpdate.pending, (state) => {
      state.itemsForActions.deletableId = null;
    });
    builder.addCase(getUsers.pending, (state) => {
      usersSlice.caseReducers.cleanupItemsForActions(state);
    });
  },
});

const { setIsLoading, cleanupUsers, setDeletableId, setSelectedItemsIds } = usersSlice.actions;
export {
  getUsers,
  refreshUsers,
  deleteUserWithUpdate,
  deleteUsersWithUpdate,
  cleanupUsers,
  setDeletableId,
  setSelectedItemsIds,
};
export default usersSlice.reducer;
