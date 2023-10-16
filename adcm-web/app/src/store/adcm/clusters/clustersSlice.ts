import { createSlice } from '@reduxjs/toolkit';
import { AdcmClustersApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmCluster } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { updateIfExists } from '@utils/objectUtils';
import { defaultSpinnerDelay } from '@constants';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';

type AdcmClustersState = {
  clusters: AdcmCluster[];
  totalCount: number;
  isLoading: boolean;
};

const loadClustersFromBackend = createAsyncThunk('adcm/clusters/loadClustersFromBackend', async (arg, thunkAPI) => {
  const {
    adcm: {
      clustersTable: { filter, paginationParams, sortParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmClustersApi.getClusters(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getClusters = createAsyncThunk('adcm/clusters/getClusters', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadClustersFromBackend());
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshClusters = createAsyncThunk('adcm/clusters/refreshClusters', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadClustersFromBackend());
});

const createInitialState = (): AdcmClustersState => ({
  clusters: [],
  totalCount: 0,
  isLoading: false,
});

const clustersSlice = createSlice({
  name: 'adcm/clusters',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClusters() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClustersFromBackend.fulfilled, (state, action) => {
      state.clusters = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadClustersFromBackend.rejected, (state) => {
      state.clusters = [];
    });
    builder.addCase(wsActions.update_cluster, (state, action) => {
      const { id, changes } = action.payload.object;
      state.clusters = updateIfExists<AdcmCluster>(
        state.clusters,
        (cluster) => cluster.id === id,
        () => changes,
      );
    });
    builder.addCase(wsActions.delete_cluster_concern, (state, action) => {
      const { id, changes } = action.payload.object;
      state.clusters = updateIfExists<AdcmCluster>(
        state.clusters,
        (cluster) => cluster.id === id,
        (cluster) => ({
          concerns: cluster.concerns.filter((concern) => concern.id !== changes.id),
        }),
      );
    });
  },
});

const { setIsLoading, cleanupClusters } = clustersSlice.actions;
export { getClusters, refreshClusters, cleanupClusters };
export default clustersSlice.reducer;
