import { ListState } from '@models/table';
import { createAsyncThunk, createListSlice } from '@store/redux';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { AdcmServicesFilter, AdcmService } from '@models/adcm';

type AdcmServicesTableState = ListState<AdcmServicesFilter> & {
  relatedData: {
    services: AdcmService[];
  };
};

const createInitialState = (): AdcmServicesTableState => ({
  filter: {
    serviceName: undefined,
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
    services: [],
  },
});

const loadServices = createAsyncThunk('adcm/servicesTable/loadServices', async (arg: number, thunkAPI) => {
  try {
    const emptyFilter = {};
    const clusters = await AdcmClusterServicesApi.getClusterServices(arg, emptyFilter);
    return clusters.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/servicesTable/loadRelatedData', async (arg: number, thunkAPI) => {
  thunkAPI.dispatch(loadServices(arg));
});

const servicesTableSlice = createListSlice({
  name: 'adcm/servicesTable',
  createInitialState,
  reducers: {
    cleanupRelatedData(state) {
      state.relatedData = createInitialState().relatedData;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadServices.fulfilled, (state, action) => {
      state.relatedData.services = action.payload;
    });
  },
});

export const {
  setPaginationParams,
  setRequestFrequency,
  cleanupRelatedData,
  setFilter,
  resetFilter,
  setSortParams,
  resetSortParams,
} = servicesTableSlice.actions;
export { loadRelatedData };
export default servicesTableSlice.reducer;
