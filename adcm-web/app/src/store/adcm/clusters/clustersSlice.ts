import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { AdcmClustersApi, AdcmPrototypesApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import type { AdcmCluster, AdcmPrototype } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { updateIfExists } from '@utils/objectUtils';
import { defaultSpinnerDelay } from '@constants';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';
import { LoadState } from '@models/loadState';
import {
  attachContractVersionsToClusters,
  getUniqueClusterPrototypeIds,
  mergeClusterPreservingContractVersion,
} from '@utils/contractVersionUtils';
import { upsertConcern } from '@utils/concernStoreUtils';

type AdcmClustersState = {
  clusters: AdcmCluster[];
  totalCount: number;
  loadState: LoadState;
};

const loadClustersFromBackend = createAsyncThunk('adcm/clusters/loadClustersFromBackend', async (_arg, thunkAPI) => {
  const {
    adcm: {
      clustersTable: { filter, paginationParams, sortParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmClustersApi.getClusters(filter, sortParams, paginationParams);
    const prototypeIds = getUniqueClusterPrototypeIds(batch.results);
    let prototypes: AdcmPrototype[] = [];
    if (prototypeIds.length) {
      try {
        const response = await AdcmPrototypesApi.getPrototypes({ ids: prototypeIds }, undefined, {
          pageNumber: 0,
          perPage: prototypeIds.length,
        });
        prototypes = response.results;
      } catch {
        prototypes = [];
      }
    }
    const results = attachContractVersionsToClusters(batch.results, prototypes);
    return { ...batch, results };
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getClusters = createAsyncThunk('adcm/clusters/getClusters', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(setLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadClustersFromBackend());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLoadState(LoadState.Loaded));
    },
  });
});

const refreshClusters = createAsyncThunk('adcm/clusters/refreshClusters', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(loadClustersFromBackend());
});

const createInitialState = (): AdcmClustersState => ({
  clusters: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
});

const clustersSlice = createSlice({
  name: 'adcm/clusters',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
    upsertCluster(state, action: PayloadAction<AdcmCluster>) {
      const { payload: cluster } = action;
      const index = state.clusters.findIndex((c) => c.id === cluster.id);
      if (index >= 0) {
        state.clusters[index] = mergeClusterPreservingContractVersion(state.clusters[index], cluster);
      }
    },
    removeCluster(state, action: PayloadAction<number>) {
      const clusterId = action.payload;
      const prevLength = state.clusters.length;
      state.clusters = state.clusters.filter((cluster) => cluster.id !== clusterId);
      if (state.clusters.length !== prevLength) {
        state.totalCount -= 1;
      }
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
        (cluster) => {
          const nextChanges: Partial<AdcmCluster> = { ...changes };
          if (changes.prototype) {
            nextChanges.prototype = {
              ...cluster.prototype,
              ...changes.prototype,
              contractVersion: changes.prototype.contractVersion ?? cluster.prototype.contractVersion,
            };
          }
          return nextChanges;
        },
      );
    });
    builder.addCase(wsActions.create_cluster_concern, (state, action) => {
      const { id: clusterId, changes: newConcern } = action.payload.object;
      state.clusters = updateIfExists<AdcmCluster>(
        state.clusters,
        (cluster) => cluster.id === clusterId,
        (cluster) => ({
          concerns: upsertConcern(cluster.concerns, newConcern),
        }),
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

const { setLoadState, cleanupClusters, upsertCluster, removeCluster } = clustersSlice.actions;
export { getClusters, refreshClusters, cleanupClusters, setLoadState, upsertCluster, removeCluster };
export default clustersSlice.reducer;
