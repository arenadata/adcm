import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import type { AdcmBundle } from '@models/adcm/bundle';
import { AdcmBundlesApi } from '@api';
import { LoadState } from '@models/loadState';

type AdcmBundlesState = {
  bundles: AdcmBundle[];
  totalCount: number;
  loadState: LoadState;
};

const loadBundles = createAsyncThunk('adcm/bundles/loadBundles', async (_arg, thunkAPI) => {
  const {
    adcm: {
      bundlesTable: { filter, sortParams, paginationParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmBundlesApi.getBundles(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getBundles = createAsyncThunk('adcm/bundles/getBundles', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(setLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadBundles());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLoadState(LoadState.Loaded));
    },
  });
});

const refreshBundles = createAsyncThunk('adcm/bundles/refreshBundles', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(loadBundles());
});

const createInitialState = (): AdcmBundlesState => ({
  bundles: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
});

const bundlesSlice = createSlice({
  name: 'adcm/bundles',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
    cleanupBundles() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadBundles.fulfilled, (state, action) => {
      state.bundles = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadBundles.rejected, (state) => {
      state.bundles = [];
    });
  },
});

export const { setLoadState, cleanupBundles } = bundlesSlice.actions;
export { getBundles, refreshBundles };

export default bundlesSlice.reducer;
