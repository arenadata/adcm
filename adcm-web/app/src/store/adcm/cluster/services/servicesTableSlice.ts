import type { ListState } from '@models/table';
import { createAsyncThunk, createListSlice } from '@store/redux';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import type { AdcmServicesFilter } from '@models/adcm';

type AdcmServicesTableState = ListState<AdcmServicesFilter>;

const createInitialState = (): AdcmServicesTableState => ({
  filter: {
    displayName: undefined,
  },
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 0,
  sortParams: {
    sortBy: 'displayName',
    sortDirection: 'asc',
  },
});

const loadServices = createAsyncThunk('adcm/servicesTable/loadServices', async (clusterId: number, thunkAPI) => {
  try {
    const emptyFilter = {};
    const clusters = await AdcmClusterServicesApi.getClusterServices(clusterId, emptyFilter);
    return clusters.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/servicesTable/loadRelatedData', async (clusterId: number, thunkAPI) => {
  thunkAPI.dispatch(loadServices(clusterId));
});

const servicesTableSlice = createListSlice({
  name: 'adcm/servicesTable',
  createInitialState,
  reducers: {},
});

export const {
  setPaginationParams,
  setRequestFrequency,
  cleanupList,
  setFilter,
  resetFilter,
  setSortParams,
  resetSortParams,
} = servicesTableSlice.actions;
export { loadRelatedData };
export default servicesTableSlice.reducer;
