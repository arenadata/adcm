import { ListState, SortParams } from '@models/table';
import { createAsyncThunk, createListSlice } from '@store/redux';
import { AdcmClusterHostsFilter } from '@models/adcm/clusterHosts';
import { AdcmHostProvider } from '@models/adcm';
import { AdcmHostProvidersApi } from '@api';

const loadHostProviders = createAsyncThunk('adcm/clusterHostsTable/hostProviders', async (arg, thunkAPI) => {
  try {
    const emptyFilter = {};
    const defaultSortParams: SortParams = { sortBy: 'name', sortDirection: 'asc' };

    const hostProviders = await AdcmHostProvidersApi.getHostProviders(emptyFilter, defaultSortParams);
    return hostProviders.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

type AdcmClusterHostsTableState = ListState<AdcmClusterHostsFilter> & {
  relatedData: {
    hostProviders: AdcmHostProvider[];
    isHostProvidersLoaded: boolean;
  };
};

const createInitialState = (): AdcmClusterHostsTableState => ({
  filter: {
    name: undefined,
    hostprovider: undefined,
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
    hostProviders: [],
    isHostProvidersLoaded: false,
  },
});

const clusterHostsTableSlice = createListSlice({
  name: 'adcm/clusterHostsTable',
  createInitialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(loadHostProviders.fulfilled, (state, action) => {
      state.relatedData.hostProviders = action.payload;
      state.relatedData.isHostProvidersLoaded = true;
    });
    builder.addCase(loadHostProviders.rejected, (state) => {
      state.relatedData.hostProviders = [];
    });
  },
});

export const {
  setPaginationParams,
  setRequestFrequency,
  cleanupList,
  setFilter,
  resetFilter,
  setSortParams,
  resetSortParams,
} = clusterHostsTableSlice.actions;

export { loadHostProviders };

export default clusterHostsTableSlice.reducer;
