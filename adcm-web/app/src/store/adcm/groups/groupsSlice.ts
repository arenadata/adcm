import { createSlice } from '@reduxjs/toolkit';
import { AdcmGroupsApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmGroup } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { rejectedFilter } from '@utils/promiseUtils';

interface AdcmGroupsState {
  groups: AdcmGroup[];
  totalCount: number;
  itemsForActions: {
    deletableId: number | null;
  };
  isLoading: boolean;
  selectedItemsIds: number[];
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

const refreshGroups = createAsyncThunk('adcm/groups/refreshGroups', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadFromBackend());
});

const deleteGroupsWithUpdate = createAsyncThunk('adcm/groups/deleteGroups', async (ids: number[], thunkAPI) => {
  try {
    const deletePromises = await Promise.allSettled(ids.map((id) => AdcmGroupsApi.deleteGroup(id)));
    const responsesList = rejectedFilter(deletePromises);

    if (responsesList.length > 0) {
      throw responsesList[0];
    }

    await thunkAPI.dispatch(getGroups());
    thunkAPI.dispatch(showInfo({ message: 'Groups have been deleted' }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const createInitialState = (): AdcmGroupsState => ({
  groups: [],
  totalCount: 0,
  itemsForActions: {
    deletableId: null,
  },
  isLoading: false,
  selectedItemsIds: [],
});

const groupsSlice = createSlice({
  name: 'adcm/groups',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupGroups() {
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
    builder
      .addCase(loadFromBackend.fulfilled, (state, action) => {
        state.groups = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(loadFromBackend.rejected, (state) => {
        state.groups = [];
      })
      .addCase(deleteGroupsWithUpdate.pending, (state) => {
        state.itemsForActions.deletableId = null;
      })
      .addCase(getGroups.pending, (state) => {
        groupsSlice.caseReducers.cleanupItemsForActions(state);
      });
  },
});

const { setIsLoading, cleanupGroups, setDeletableId, setSelectedItemsIds } = groupsSlice.actions;
export { getGroups, refreshGroups, deleteGroupsWithUpdate, cleanupGroups, setDeletableId, setSelectedItemsIds };
export default groupsSlice.reducer;
