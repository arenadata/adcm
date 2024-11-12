import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { LoadState } from '@models/loadState';
import type { AdcmActionHostGroup } from '@models/adcm/actionHostGroup';
import type { GetActionHostGroupsActionPayload } from './actionHostGroups.types';
import { services } from './actionHostGroupsSlice.constants';

type AdcmActionHostGroupsState = {
  actionHostGroups: AdcmActionHostGroup[];
  totalCount: number;
  loadState: LoadState;
};

const loadActionHostGroupsFromBackend = createAsyncThunk(
  'adcm/actionHostGroups/loadActionHostGroupsFromBackend',
  async ({ entityType, entityArgs }: GetActionHostGroupsActionPayload, thunkAPI) => {
    try {
      const service = services[entityType];
      const {
        adcm: {
          actionHostGroupsTable: { filter, paginationParams },
        },
      } = thunkAPI.getState();

      const batch = await service.getActionHostGroups({ ...entityArgs, filter, paginationParams });
      return batch;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getActionHostGroups = createAsyncThunk(
  'adcm/actionHostGroups/getActionHostGroups',
  async (args: GetActionHostGroupsActionPayload, thunkAPI) => {
    thunkAPI.dispatch(setLoadState(LoadState.Loading));
    const startDate = new Date();

    await thunkAPI.dispatch(loadActionHostGroupsFromBackend(args));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setLoadState(LoadState.Loaded));
      },
    });
  },
);

const createInitialState = (): AdcmActionHostGroupsState => ({
  actionHostGroups: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
});

const actionHostGroupsSlice = createSlice({
  name: 'adcm/actionHostGroups',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
    cleanupActionHostGroups() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadActionHostGroupsFromBackend.fulfilled, (state, action) => {
      state.actionHostGroups = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadActionHostGroupsFromBackend.rejected, (state) => {
      state.actionHostGroups = [];
    });
  },
});

const { setLoadState, cleanupActionHostGroups } = actionHostGroupsSlice.actions;
export { getActionHostGroups, cleanupActionHostGroups };
export default actionHostGroupsSlice.reducer;
