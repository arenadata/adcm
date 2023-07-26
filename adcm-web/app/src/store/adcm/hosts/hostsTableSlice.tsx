import { ListState, SortParams } from '@models/table';
import { createAsyncThunk, createListSlice } from '@store/redux';
import { AdcmClustersApi, AdcmHostProvidersApi } from '@api';
import { AdcmCluster, AdcmHostProvider, AdcmHostsFilter } from '@models/adcm';

type AdcmHostsTableState = ListState<AdcmHostsFilter> & {
  relatedData: {
    clusters: AdcmCluster[];
    hostProviders: AdcmHostProvider[];
  };
};

const createInitialState = (): AdcmHostsTableState => ({
  filter: {
    hostName: undefined,
    hostProvider: undefined,
    clusterName: undefined,
  },
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 0,
  sortParams: {
    sortBy: '',
    sortDirection: 'asc',
  },
  relatedData: {
    clusters: [],
    hostProviders: [],
  },
});

const loadClusters = createAsyncThunk('adcm/hostsTable/loadClusters', async (arg, thunkAPI) => {
  try {
    const emptyFilter = {};
    const defaultPaginationParams = { perPage: 999, pageNumber: 0 };

    const clusters = await AdcmClustersApi.getClusters(emptyFilter, defaultPaginationParams);
    return clusters;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadHostProviders = createAsyncThunk('adcm/hostsTable/HostProviders', async (arg, thunkAPI) => {
  try {
    const emptyFilter = {};
    const defaultSortParams: SortParams = { sortBy: 'name', sortDirection: 'asc' };
    const defaultPaginationParams = { perPage: 999, pageNumber: 0 };

    const hostProviders = await AdcmHostProvidersApi.getHostProviders(
      emptyFilter,
      defaultSortParams,
      defaultPaginationParams,
    );
    return hostProviders;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/hostsTable/loadRelatedData', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadClusters());
  thunkAPI.dispatch(loadHostProviders());
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
      state.relatedData.clusters = action.payload.results;
    });
    builder.addCase(loadHostProviders.fulfilled, (state, action) => {
      state.relatedData.hostProviders = action.payload.results;
    });
  },
});

export const { setPaginationParams, setRequestFrequency, cleanupList, cleanupRelatedData, setFilter, resetFilter } =
  hostsTableSlice.actions;
export { loadRelatedData };
export default hostsTableSlice.reducer;
