import type { ListState, SortParams } from '@models/table';
import { createAsyncThunk, createListSlice } from '@store/redux';
import { AdcmClustersApi, AdcmHostProvidersApi } from '@api';
import type { AdcmCluster, AdcmHostProvider, AdcmHostsFilter } from '@models/adcm';

type AdcmHostsTableState = ListState<AdcmHostsFilter> & {
  relatedData: {
    clusters: AdcmCluster[];
    hostProviders: AdcmHostProvider[];
    isClustersLoaded: boolean;
    isHostProvidersLoaded: boolean;
  };
  isAllDataLoaded: boolean;
};

const createInitialState = (): AdcmHostsTableState => ({
  filter: {
    name: undefined,
    hostproviderName: undefined,
    clusterName: undefined,
  },
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 0,
  sortParams: {
    sortBy: 'name',
    sortDirection: 'asc',
  },
  relatedData: {
    clusters: [],
    isClustersLoaded: false,
    hostProviders: [],
    isHostProvidersLoaded: false,
  },
  isAllDataLoaded: false,
});

const loadClusters = createAsyncThunk('adcm/hostsTable/loadClusters', async (arg, thunkAPI) => {
  try {
    const emptyFilter = {};
    const clusters = await AdcmClustersApi.getClusters(emptyFilter);
    return clusters.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadHostProviders = createAsyncThunk('adcm/hostsTable/hostProviders', async (arg, thunkAPI) => {
  try {
    const emptyFilter = {};
    const defaultSortParams: SortParams = { sortBy: 'name', sortDirection: 'asc' };

    const hostProviders = await AdcmHostProvidersApi.getHostProviders(emptyFilter, defaultSortParams);
    return hostProviders.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/hostsTable/loadRelatedData', async (arg, thunkAPI) => {
  await Promise.all([thunkAPI.dispatch(loadClusters()), thunkAPI.dispatch(loadHostProviders())]);
});

const hostsTableSlice = createListSlice({
  name: 'adcm/hostsTable',
  createInitialState,
  reducers: {
    cleanupRelatedData(state) {
      state.relatedData = createInitialState().relatedData;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusters.fulfilled, (state, action) => {
      state.relatedData.clusters = action.payload;
      state.relatedData.isClustersLoaded = true;
    });
    builder.addCase(loadClusters.rejected, (state) => {
      state.relatedData.clusters = [];
    });
    builder.addCase(loadHostProviders.fulfilled, (state, action) => {
      state.relatedData.hostProviders = action.payload;
      state.relatedData.isHostProvidersLoaded = true;
    });
    builder.addCase(loadHostProviders.rejected, (state) => {
      state.relatedData.hostProviders = [];
    });
    builder.addCase(loadRelatedData.fulfilled, (state) => {
      state.isAllDataLoaded = state.relatedData.isClustersLoaded && state.relatedData.isHostProvidersLoaded;
    });
  },
});

export const {
  setPaginationParams,
  setRequestFrequency,
  cleanupList,
  cleanupRelatedData,
  setFilter,
  resetFilter,
  setSortParams,
  resetSortParams,
} = hostsTableSlice.actions;
export { loadRelatedData };
export default hostsTableSlice.reducer;
