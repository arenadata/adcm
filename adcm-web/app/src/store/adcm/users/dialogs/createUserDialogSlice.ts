import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmGroup, AdcmCreateUserPayload } from '@models/adcm';
import { AdcmGroupsApi, AdcmUsersApi, RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getUsers } from '@store/adcm/users/usersSlice';

type AdcmCreateUserState = {
  isOpen: boolean;
  relatedData: {
    groups: AdcmGroup[];
    isLoaded: boolean;
  };
};

const createInitialState = (): AdcmCreateUserState => ({
  isOpen: false,
  relatedData: {
    groups: [],
    isLoaded: false,
  },
});

const createUser = createAsyncThunk(
  'adcm/user/createUserDialog/createUser',
  async (arg: AdcmCreateUserPayload, thunkAPI) => {
    try {
      await AdcmUsersApi.createUser(arg);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getUsers());
    }
  },
);

const loadGroups = createAsyncThunk('adcm/user/createUserDialog/loadGroups', async (arg, thunkAPI) => {
  try {
    const groups = await AdcmGroupsApi.getGroups();
    return groups;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/user/createUserDialog/loadRelatedData', async (arg, thunkAPI) => {
  await thunkAPI.dispatch(loadGroups());
});

const open = createAsyncThunk('adcm/user/createUserDialog/open', async (arg, thunkAPI) => {
  try {
    thunkAPI.dispatch(loadRelatedData());
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createUserDialogSlice = createSlice({
  name: 'adcm/user/createUserDialog',
  initialState: createInitialState(),
  reducers: {
    close() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(open.fulfilled, (state) => {
      state.isOpen = true;
    });
    builder.addCase(loadRelatedData.fulfilled, (state) => {
      state.relatedData.isLoaded = true;
    });
    builder.addCase(loadGroups.fulfilled, (state, action) => {
      state.relatedData.groups = action.payload.results;
    });
    builder.addCase(createUser.fulfilled, () => {
      return createInitialState();
    });
  },
});

const { close } = createUserDialogSlice.actions;
export { open, close, createUser };
export default createUserDialogSlice.reducer;
