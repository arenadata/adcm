import { createAsyncThunk, createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmBundlesFilter } from '@models/adcm/bundle';
import { AdcmPrototypesApi } from '@api';
import { AdcmProduct, AdcmPrototypeType } from '@models/adcm';
import { deleteBundles, getBundles } from '@store/adcm/bundles/bundlesSlice';

type AdcmBundlesTableState = ListState<AdcmBundlesFilter> & {
  relatedData: {
    products: AdcmProduct[];
  };
  itemsForActions: {
    deletableId: number | null;
  };
  selectedItemsIds: number[];
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
    sortBy: '',
    sortDirection: 'asc',
  },
  relatedData: {
    products: [],
  },
  itemsForActions: {
    deletableId: null,
  },
  selectedItemsIds: [],
});

const loadPrototypeVersions = createAsyncThunk('adcm/bundlesTable/loadPrototype', async (arg, thunkAPI) => {
  try {
    const prototypesWithVersions = await AdcmPrototypesApi.getPrototypeVersions({ type: AdcmPrototypeType.Cluster });
    return prototypesWithVersions;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/bundlesTable/loadRelatedData', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadPrototypeVersions());
});

const bundlesTableSlice = createListSlice({
  name: 'adcm/bundlesTable',
  createInitialState,
  reducers: {
    cleanupRelatedData(state) {
      state.relatedData = createInitialState().relatedData;
    },
    cleanupItemsForActions(state) {
      state.itemsForActions = createInitialState().itemsForActions;
    },
    setSelectedItemsIds(state, action) {
      state.selectedItemsIds = action.payload;
    },
    setDeletableId(state, action) {
      state.itemsForActions.deletableId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadPrototypeVersions.fulfilled, (state, action) => {
      state.relatedData.products = action.payload.map(({ name, displayName }) => ({ name, displayName }));
    });
    builder.addCase(deleteBundles.pending, (state) => {
      // hide dialog, when
      bundlesTableSlice.caseReducers.setDeletableId(state, {
        payload: null,
        type: 'adcm/bundlesTables/setDeletableId',
      });
    });
    builder.addCase(getBundles.pending, (state) => {
      // hide dialogs, when load new bundles list (not silent refresh)
      bundlesTableSlice.caseReducers.cleanupItemsForActions(state);
    });
    // brake selected rows after full update
    builder.addCase(getBundles.fulfilled, (state) => {
      state.selectedItemsIds = [];
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
  setDeletableId,
  cleanupItemsForActions,
  setSelectedItemsIds,
} = bundlesTableSlice.actions;
export { loadRelatedData };
export default bundlesTableSlice.reducer;
