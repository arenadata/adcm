import { createSlice } from '@reduxjs/toolkit';
import { AdcmGroupsApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmGroup } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { LoadState } from '@models/loadState';

interface AdcmGroupsState {
  groups: AdcmGroup[];
  totalCount: number;
  loadState: LoadState;
}

const loadFromBackend = createAsyncThunk('adcm/groups/loadFromBackend', async (arg, thunkAPI) => {
  const {
    adcm: {
      groupsTable: { filter, paginationParams, sortParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmGroupsApi.getGroups(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getGroups = createAsyncThunk('adcm/groups/getGroups', async (arg, thunkAPI) => {
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

const refreshGroups = createAsyncThunk('adcm/groups/refreshGroups', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadFromBackend());
});

const createInitialState = (): AdcmGroupsState => ({
  groups: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
});

const groupsSlice = createSlice({
  name: 'adcm/groups',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
    cleanupGroups() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadFromBackend.fulfilled, (state, action) => {
        state.groups = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(loadFromBackend.rejected, (state) => {
        state.groups = [];
      });
  },
});

const { setLoadState, cleanupGroups } = groupsSlice.actions;
export { getGroups, refreshGroups, cleanupGroups };
export default groupsSlice.reducer;
