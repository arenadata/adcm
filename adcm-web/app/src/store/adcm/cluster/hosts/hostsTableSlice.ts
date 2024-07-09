import type { ListState, SortParams } from '@models/table';
import { createAsyncThunk, createListSlice } from '@store/redux';
import type { AdcmClusterHostsFilter } from '@models/adcm/clusterHosts';
import type { AdcmHostProvider, AdcmMappingComponent } from '@models/adcm';
import { AdcmClusterMappingApi, AdcmHostProvidersApi, RequestError } from '@api';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

interface ClusterHostComponentsPayload {
  clusterId: number;
}

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

const loadHostComponents = createAsyncThunk(
  'adcm/clusterHostsTable/hostComponents',
  async ({ clusterId }: ClusterHostComponentsPayload, thunkAPI) => {
    try {
      // we use method from mapping, because we need full list of components for filter in cluster hosts page
      const clusterHostComponents = await AdcmClusterMappingApi.getMappingComponents(clusterId);

      return clusterHostComponents;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

type AdcmClusterHostsTableState = ListState<AdcmClusterHostsFilter> & {
  relatedData: {
    hostProviders: AdcmHostProvider[];
    hostComponents: AdcmMappingComponent[];
    isHostProvidersLoaded: boolean;
    isHostComponentsLoaded: boolean;
  };
};

export const createInitialState = (): AdcmClusterHostsTableState => ({
  filter: {
    name: undefined,
    hostproviderName: undefined,
    componentId: undefined,
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
    hostComponents: [],
    isHostProvidersLoaded: false,
    isHostComponentsLoaded: false,
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
    builder.addCase(loadHostComponents.fulfilled, (state, action) => {
      state.relatedData.hostComponents = action.payload;
      state.relatedData.isHostComponentsLoaded = true;
    });
    builder.addCase(loadHostComponents.rejected, (state) => {
      state.relatedData.hostComponents = [];
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

export { loadHostProviders, loadHostComponents };

export default clusterHostsTableSlice.reducer;
