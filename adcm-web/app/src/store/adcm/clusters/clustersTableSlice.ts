import { createListSlice, createAsyncThunk } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmPrototypesApi } from '@api';
import { AdcmClustersFilter, PrototypeType } from '@models/adcm';

type AdcmClustersTableState = ListState<AdcmClustersFilter> & {
  relatedData: {
    prototypeNames: string[];
  };
};

const createInitialState = (): AdcmClustersTableState => ({
  filter: {
    clusterName: undefined,
    clusterStatus: undefined,
    prototypeName: undefined,
  },
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 5,
  sortParams: {
    sortBy: '',
    sortDirection: 'asc',
  },
  relatedData: {
    prototypeNames: [],
  },
});

const loadPrototypeVersions = createAsyncThunk('adcm/clusters/loadPrototypeVersions', async (arg, thunkAPI) => {
  try {
    const prototypeVersions = await AdcmPrototypesApi.getPrototypeVersions({ type: PrototypeType.Cluster });
    return prototypeVersions;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/clusters/loadRelatedData', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadPrototypeVersions());
});

const clustersTableSlice = createListSlice({
  name: 'adcm/clustersTable',
  createInitialState,
  reducers: {
    cleanupRelatedData(state) {
      state.relatedData.prototypeNames = [];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadPrototypeVersions.fulfilled, (state, action) => {
      const prototypeNames = action.payload.map((x) => x.name);
      state.relatedData.prototypeNames = [...new Set(prototypeNames)];
    });
  },
});

export const { setPaginationParams, setRequestFrequency, cleanupList, setFilter, resetFilter, cleanupRelatedData } =
  clustersTableSlice.actions;
export { loadRelatedData };
export default clustersTableSlice.reducer;
