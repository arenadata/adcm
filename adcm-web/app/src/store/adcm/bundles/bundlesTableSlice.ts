import { createAsyncThunk, createListSlice } from '@store/redux';
import type { ListState } from '@models/table';
import type { AdcmBundlesFilter } from '@models/adcm/bundle';
import { AdcmPrototypesApi } from '@api';
import type { AdcmPrototypeVersions } from '@models/adcm';
import { AdcmPrototypeType } from '@models/adcm';
import { LoadState } from '@models/loadState';

type AdcmBundlesTableState = ListState<AdcmBundlesFilter> & {
  relatedData: {
    products: AdcmPrototypeVersions[];
    productsLoadState: LoadState;
  };
};

const createInitialState = (): AdcmBundlesTableState => ({
  filter: {
    displayName: undefined,
    product: undefined,
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
  relatedData: {
    products: [],
    productsLoadState: LoadState.NotLoaded,
  },
});

const loadPrototypeVersions = createAsyncThunk('adcm/bundlesTable/loadPrototype', async (_arg, thunkAPI) => {
  try {
    const prototypesWithVersions = await Promise.all([
      AdcmPrototypesApi.getPrototypeVersions({ type: AdcmPrototypeType.Cluster }),
      AdcmPrototypesApi.getPrototypeVersions({ type: AdcmPrototypeType.Provider }),
    ]);
    return prototypesWithVersions.flat();
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/bundlesTable/loadRelatedData', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(loadPrototypeVersions());
});

const bundlesTableSlice = createListSlice({
  name: 'adcm/bundlesTable',
  createInitialState,
  reducers: {
    cleanupRelatedData(state) {
      state.relatedData = createInitialState().relatedData;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadPrototypeVersions.fulfilled, (state, action) => {
      state.relatedData.products = action.payload;
      state.relatedData.productsLoadState = LoadState.Loaded;
    });
    builder.addCase(loadPrototypeVersions.rejected, (state) => {
      state.relatedData.products = [];
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
} = bundlesTableSlice.actions;
export { loadRelatedData };
export default bundlesTableSlice.reducer;
