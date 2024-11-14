import type { ListState } from '@models/table';
import { createAsyncThunk, createListSlice } from '@store/redux';
import type { AdcmClusterImportServiceFilter, AdcmService } from '@models/adcm';
import { AdcmServicesApi } from '@api';

type GetClusterServiceImportsArg = {
  clusterId: number;
};

type AdcmImportClusterServiceFilterState = ListState<AdcmClusterImportServiceFilter> & {
  relatedData: {
    serviceList: AdcmService[];
  };
};

const createInitialState = (): AdcmImportClusterServiceFilterState => ({
  filter: {
    serviceId: null,
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
    serviceList: [],
  },
});

const loadServiceList = createAsyncThunk(
  'adcm/cluster/imports/clusterServiceFilter/loadServiceList',
  async ({ clusterId }: GetClusterServiceImportsArg, thunkAPI) => {
    try {
      const serviceList = await AdcmServicesApi.getServices(clusterId);
      return serviceList;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadRelatedData = createAsyncThunk(
  'adcm/cluster/imports/clusterServiceFilter/loadRelatedData',
  async ({ clusterId }: GetClusterServiceImportsArg, thunkAPI) => {
    thunkAPI.dispatch(loadServiceList({ clusterId }));
  },
);

const clusterImportServiceFilterSlice = createListSlice({
  name: 'adcm/cluster/imports/clusterServiceFilter',
  createInitialState,
  reducers: {
    cleanupRelatedData(state) {
      state.relatedData.serviceList = [];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadServiceList.fulfilled, (state, action) => {
      state.relatedData.serviceList = action.payload.results;
    });
    builder.addCase(loadServiceList.rejected, (state) => {
      state.relatedData.serviceList = [];
    });
  },
});

export const { setPaginationParams, setSortParams, cleanupRelatedData, setFilter, resetFilter } =
  clusterImportServiceFilterSlice.actions;
export { loadRelatedData };
export default clusterImportServiceFilterSlice.reducer;
