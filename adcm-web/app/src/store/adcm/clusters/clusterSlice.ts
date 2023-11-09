import { AdcmClustersApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmCluster } from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';
import { showError } from '@store/notificationsSlice';

interface AdcmClusterState {
  cluster?: AdcmCluster;
  isLoading: boolean;
}

const loadClusterFromBackend = createAsyncThunk(
  'adcm/cluster/loadClusterFromBackend',
  async (arg: number, thunkAPI) => {
    try {
      const cluster = await AdcmClustersApi.getCluster(arg);
      return cluster;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: `Cluster with id = ${arg} not found` }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getCluster = createAsyncThunk('adcm/cluster/getCluster', async (arg: number, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadClusterFromBackend(arg));

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,

    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const createInitialState = (): AdcmClusterState => ({
  cluster: undefined,
  isLoading: false,
});

const clusterSlice = createSlice({
  name: 'adcm/cluster',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupCluster() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterFromBackend.fulfilled, (state, action) => {
      state.cluster = action.payload;
    });
    builder.addCase(loadClusterFromBackend.rejected, (state) => {
      state.cluster = undefined;
    });
    builder.addCase(wsActions.update_cluster, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.cluster?.id == id) {
        state.cluster = {
          ...state.cluster,
          ...changes,
        };
      }
    });
    builder.addCase(wsActions.create_cluster_concern, (state, action) => {
      const { id: clusterId, changes: newConcern } = action.payload.object;
      if (state.cluster?.id === clusterId && state.cluster.concerns.every((concern) => concern.id !== newConcern.id)) {
        state.cluster = {
          ...state.cluster,
          concerns: [...state.cluster.concerns, newConcern],
        };
      }
    });
    builder.addCase(wsActions.delete_cluster_concern, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.cluster?.id === id) {
        state.cluster = {
          ...state.cluster,
          concerns: state.cluster.concerns.filter((concern) => concern.id !== changes.id),
        };
      }
    });
  },
});

const { setIsLoading, cleanupCluster } = clusterSlice.actions;
export { getCluster, cleanupCluster };
export default clusterSlice.reducer;
