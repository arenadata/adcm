import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { AdcmClusterMetricsApi } from '@api';
import type { AdcmClusterMetrics } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { LoadState } from '@models/loadState';

type ClustersMetricsState = {
  metricsByClusterId: Record<number, AdcmClusterMetrics>;
  loadState: LoadState;
};

const createInitialState = (): ClustersMetricsState => ({
  metricsByClusterId: {},
  loadState: LoadState.NotLoaded,
});

const loadClustersMetrics = createAsyncThunk('adcm/clustersMetrics/load', async (clusterIds: number[], thunkAPI) => {
  if (!clusterIds.length) {
    return {} as Record<number, AdcmClusterMetrics>;
  }

  try {
    const results = await Promise.all(
      clusterIds.map(async (clusterId) => {
        try {
          const metrics = await AdcmClusterMetricsApi.getClusterMetrics(clusterId);
          return [clusterId, metrics] as const;
        } catch {
          return null;
        }
      }),
    );

    return Object.fromEntries(results.filter(Boolean) as Array<readonly [number, AdcmClusterMetrics]>);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const clustersMetricsSlice = createSlice({
  name: 'adcm/clustersMetrics',
  initialState: createInitialState(),
  reducers: {
    cleanupClustersMetrics() {
      return createInitialState();
    },
    setMetricsLoadState(state, action: PayloadAction<LoadState>) {
      state.loadState = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClustersMetrics.pending, (state) => {
      state.loadState = LoadState.Loading;
    });
    builder.addCase(loadClustersMetrics.fulfilled, (state, action) => {
      state.metricsByClusterId = {
        ...state.metricsByClusterId,
        ...action.payload,
      };
      state.loadState = LoadState.Loaded;
    });
    builder.addCase(loadClustersMetrics.rejected, (state) => {
      state.loadState = LoadState.Loaded;
    });
  },
});

const { cleanupClustersMetrics, setMetricsLoadState } = clustersMetricsSlice.actions;
export { loadClustersMetrics, cleanupClustersMetrics, setMetricsLoadState };
export default clustersMetricsSlice.reducer;
