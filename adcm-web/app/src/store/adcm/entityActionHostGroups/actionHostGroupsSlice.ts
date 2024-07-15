import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterActionHostGroupsApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { LoadState } from '@models/loadState';
import type { AdcmActionHostGroup } from '@models/adcm/actionHostGroup';

type AdcmClusterActionHostGroupsState = {
  actionHostGroups: AdcmActionHostGroup[];
  totalCount: number;
  loadState: LoadState;
};

type GetClusterActionHostGroupsArgs = {
  clusterId: number;
};

type DeleteClusterActionHostsGroupArgs = {
  clusterId: number;
  actionHostGroupId: number;
};

const loadClusterActionHostGroupsFromBackend = createAsyncThunk(
  'adcm/clusterActionHostGroups/loadClusterActionHostGroupsFromBackend',
  async (clusterId: number, thunkAPI) => {
    try {
      const batch = await AdcmClusterActionHostGroupsApi.getActionHostGroups(clusterId, { pageNumber: 0, perPage: 10 });
      return batch;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterActionHostGroups = createAsyncThunk(
  'adcm/clusterActionHostGroups/getClusterActionHostGroups',
  async ({ clusterId }: GetClusterActionHostGroupsArgs, thunkAPI) => {
    thunkAPI.dispatch(setLoadState(LoadState.Loading));
    const startDate = new Date();

    await thunkAPI.dispatch(loadClusterActionHostGroupsFromBackend(clusterId));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setLoadState(LoadState.Loaded));
      },
    });
  },
);

const deleteClusterActionHostGroup = createAsyncThunk(
  'adcm/clusterActionHostGroups/deleteClusterActionHostGroup',
  async (args: DeleteClusterActionHostsGroupArgs, thunkAPI) => {
    try {
      await AdcmClusterActionHostGroupsApi.deleteActionHostGroup(args.clusterId, args.actionHostGroupId);
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmClusterActionHostGroupsState => ({
  actionHostGroups: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
});

const clusterHostsSlice = createSlice({
  name: 'adcm/clusterActionHostGroups',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
    cleanupClusterActionHostGroups() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterActionHostGroupsFromBackend.fulfilled, (state, action) => {
      state.actionHostGroups = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadClusterActionHostGroupsFromBackend.rejected, (state) => {
      state.actionHostGroups = [];
    });
  },
});

const { setLoadState, cleanupClusterActionHostGroups } = clusterHostsSlice.actions;
export { getClusterActionHostGroups, cleanupClusterActionHostGroups, deleteClusterActionHostGroup };
export default clusterHostsSlice.reducer;
