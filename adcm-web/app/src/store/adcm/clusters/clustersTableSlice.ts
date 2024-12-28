import { createListSlice, createAsyncThunk } from '@store/redux';
import type { ListState } from '@models/table';
import { AdcmPrototypesApi } from '@api';
import type { AdcmClustersFilter, AdcmPrototypeVersions } from '@models/adcm';
import { AdcmPrototypeType } from '@models/adcm';

type AdcmClustersTableState = ListState<AdcmClustersFilter> & {
  relatedData: {
    prototypes: AdcmPrototypeVersions[];
  };
  isAllDataLoaded: boolean;
};

const createInitialState = (): AdcmClustersTableState => ({
  filter: {
    name: undefined,
    status: undefined,
    prototypeName: undefined,
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
    prototypes: [],
  },
  isAllDataLoaded: false,
});

const loadPrototypeVersions = createAsyncThunk('adcm/clusters/loadPrototypeVersions', async (_arg, thunkAPI) => {
  try {
    const prototypeVersions = await AdcmPrototypesApi.getPrototypeVersions({ type: AdcmPrototypeType.Cluster });
    return prototypeVersions;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/clusters/loadRelatedData', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(loadPrototypeVersions());
});

const clustersTableSlice = createListSlice({
  name: 'adcm/clustersTable',
  createInitialState,
  reducers: {
    cleanupRelatedData(state) {
      state.relatedData.prototypes = [];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadPrototypeVersions.fulfilled, (state, action) => {
      state.relatedData.prototypes = action.payload;
      state.isAllDataLoaded = true;
    });
    builder.addCase(loadPrototypeVersions.rejected, (state) => {
      state.relatedData.prototypes = [];
    });
  },
});

export const {
  setPaginationParams,
  setRequestFrequency,
  cleanupList,
  setFilter,
  resetFilter,
  cleanupRelatedData,
  setSortParams,
  resetSortParams,
} = clustersTableSlice.actions;
export { loadRelatedData };
export default clustersTableSlice.reducer;
