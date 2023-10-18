import { AdcmHostProviderFilter, AdcmPrototypeType, AdcmPrototypeVersions } from '@models/adcm';
import { createAsyncThunk, createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmPrototypesApi } from '@api';

type AdcmHostProviderTableState = ListState<AdcmHostProviderFilter> & {
  relatedData: {
    prototypes: Pick<AdcmPrototypeVersions, 'name' | 'displayName'>[];
  };
};

const createInitialState = (): AdcmHostProviderTableState => ({
  filter: {
    name: undefined,
    prototype: undefined,
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
});

const loadPrototypes = createAsyncThunk('adcm/hostProvidersTable/loadPrototype', async (arg, thunkAPI) => {
  try {
    const prototypesWithVersions = await AdcmPrototypesApi.getPrototypeVersions({ type: AdcmPrototypeType.Provider });
    return prototypesWithVersions;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadRelatedData = createAsyncThunk('adcm/hostProvidersTable/loadRelatedData', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadPrototypes());
});

const hostProviderTableSlice = createListSlice({
  name: 'adcm/hostProvidersTable',
  createInitialState,
  reducers: {
    cleanupRelatedData(state) {
      state.relatedData = createInitialState().relatedData;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadPrototypes.fulfilled, (state, action) => {
      state.relatedData.prototypes = action.payload.map(({ name, displayName }) => ({ name, displayName }));
    });
  },
});

export const { setPaginationParams, setSortParams, setRequestFrequency, cleanupRelatedData, setFilter, resetFilter } =
  hostProviderTableSlice.actions;
export { loadRelatedData };
export default hostProviderTableSlice.reducer;
